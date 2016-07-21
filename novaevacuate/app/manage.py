import time
from novaevacuate.novacheck.network.network import get_net_status as network_check
from novaevacuate.novacheck.service.service import get_service_status as service_check
from novaevacuate.novacheck.network.network import leader
from novaevacuate.novacheck.network.network import network_retry
from novaevacuate.novacheck.service.service import novaservice_retry
from novaevacuate.novacheck.ipmi.ipmi import get_ipmi_status as ipmi_check
from novaevacuate.log import logger
from novaevacuate.fence_agent import FENCE_NODES

FENCE_NODE = FENCE_NODES

class item:
    def __init__(self):
        self.node = "null"
        self.name = "null"
        self.status = "null"
        self.ip = "null"


def manager():
    if leader() == "true":
        logger.info("Openstack nova evacuate start check")
        # ipmi_checks = ipmi_check()
        net_checks = network_check()
        ser_checks = service_check()
    else:
        time.sleep(10)
        pass
    # get network  error list
    NETERR_NODE = []
    for net_check in net_checks:
        # default network check return error data ,when network check right,
        # the return none define neterr_node save network check error return data

        network = item()
        network.node = net_check['name']
        network.name = net_check['net_role']
        network.status = net_check['status']
        network.ip = net_check['addr']
        NETERR_NODE.append(network.node)

        if network.status == "true":
            logger.info("%s %s status is: %s (%s)" %(network.node, network.name,
                                                     network.status,network.ip))
        else:
            if network.node in FENCE_NODE:
                logger.info("%s has been fence status,do not execute network"
                            "retry check" % network.node )
            else:
                logger.error("%s %s status is: %s (%s)" % (network.node, network.name,
                                                           network.status,network.ip))
                network_retry(network.node, network.name)

    for ser_check in ser_checks:
        service = item()
        service.node = ser_check['node']
        service.type = ser_check['type']
        service.status = ser_check['status']

        # when compute node recovery, will remove node from FENCE_NODES node name
        if service.node in FENCE_NODE:
            if (service.node not in NETERR_NODE) and (service.status == "up"):
                FENCE_NODE.remove(service.node)

        if service.status == "up":
            logger.info("%s %s status is: %s" %(service.node, service.type,
                                                service.status))
        elif service.status == "down" or service.status == "unknown":
            if service.node in FENCE_NODE:
                logger.info("%s %s status is: %s" %(service.node, service.type,
                                                    service.status))
                logger.info("%s has been fence status, do not execute service"
                            "retry check" % service.node)
            else:
                logger.error("%s %s status is: %s" %
                             (service.node, service.name, service.status))
                novaservice_retry(service.node, service.type)
