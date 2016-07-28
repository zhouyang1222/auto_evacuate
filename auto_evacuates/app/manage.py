from auto_evacuates.novacheck.network.network import Net_Interface
from auto_evacuates.novacheck.service.service import ServiceManage
from auto_evacuates.novacheck.ipmi.ipmi import get_ipmi_status as ipmi_check
from auto_evacuates.log import logger
from auto_evacuates.fence_agent import FENCE_NODES
from auto_evacuates.fence_agent import Fence
from auto_evacuates.evacuate_vm_action import EvacuateVmAction
import time

FENCE_NODE = FENCE_NODES


class Manager(object):
    def __init__(self):
        self.net_obj = Net_Interface()
        self.service_obj = ServiceManage()

    def run(self):
        """run all methods"""
        logger.info("Start check network")
        self.net_checks = self._check_network()
        for net_check in self.net_checks:
            # default network check return error data ,
            # when network check  right,
            # the return none define neterr_node save network check error
            # return data
            network_node = net_check['name']
            network_name = net_check['net_role']
            network_status = net_check['status']
            network_ip = net_check['addr']
            if network_node in FENCE_NODE:
                logger.info("%s has been fence status,do not execute network"
                            "retry check" % network_node)
            else:
                logger.error("%s %s status is: %s (%s)" %
                             (network_node, network_name,
                              network_status, network_ip))
                logger.info("Start recover netowork")
                network_recover_result = self._recover_network(network_node,
                                                               network_name)
                if not network_recover_result:
                    logger.info("Start fence node")
                    fence_result = self._fence('network',
                                               network_node,
                                               network_name)
                    if fence_result:
                        self._fence_node_add(network_node)
                        logger.info("Start evacuate instances from error node")
                        self._evacuate(network_node)
                    else:
                        logger.error("fence %s error" % network_node)
                else:
                    logger.info("%s %s has auto recovery" % (network_node,
                                                             network_name))
        logger.info("Start check service")
        self.service_checks = self._check_service()
        for service_check in self.service_checks:
            service_node = service_check['node']
            service_type = service_check['datatype']
            service_status = service_check['status']
            if service_node in FENCE_NODE:
                logger.info("%s has been fence status,do not execute service"
                            "retry check" % service_node)
            else:
                if service_status == "up":
                    logger.info("%s %s status is: up" % (service_node,
                                                         service_type))
                elif service_status == "down" or service_status == "unknown":
                        logger.error("%s %s status is: %s" %
                                     (service_node,
                                      service_type,
                                      service_status))
                        service_recover_result = self._recover_service(
                                                               service_node,
                                                               service_type
                                                               )
                        if not service_recover_result:
                            logger.info("Start fence node")
                            fence_result = self._fence('service',
                                                       service_node,
                                                       service_type)
                            if fence_result:
                                self._fence_node_add(service_node)
                            else:
                                logger.error("fence %s error" % network_node)

                        else:
                            logger.info("%s %s has auto recovery" %
                                        (service_node, service_type))
        self._fence_node_remove()

    def _check_network(self):
        return self.net_obj.get_net_status()

    def _check_service(self):
        return self.service_obj.get_service_status()

    def _recover_network(self, node, name):
        """
        include retry and recovey
        """
        time.sleep(10)
        flag = 0
        while flag < 3:
            retry_result = self.net_obj.network_confirm(node, name)
            if retry_result:
                return True
            flag = flag + 1
        if self.net_obj.network_recover(node, name):
            return True
        return False

    def _recover_service(self, node, datatype):
        """
        include retry
        """
        for i in range(3):
            retry_result = self.service_obj.service_retry(node, datatype)
            if retry_result:
                return True
        return False

    def _fence(self, role, node, name):
        fence = Fence()
        return fence.compute_fence(role, node, name)

    def _evacuate(self, node):
        evacuate = EvacuateVmAction(node)
        evacuate.run()

    def _fence_node_remove(self):
        """
        remove node from FENCE_NODE
        """
        error_network_node = [net_check['name']
                              for net_check in self.net_checks]
        for service_check in self.service_checks:
            service_node = service_check['node']
            service_status = service_check['status']
            if service_node in FENCE_NODE:
                if (service_node not in error_network_node) and \
                        (service_status == 'up'):
                    FENCE_NODE.remove(service_node)

    def _fence_node_add(self, node):
        """
        add node from FENCE_NODE
        """
        FENCE_NODES.append(node)
