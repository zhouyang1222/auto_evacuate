"""
Nova service check record all data
If nova service check get service false, the nova service will be execute nova
service-disable node, but do not execute evacuate.
"""
import commands
import time
import eventlet
from auto_evacuates.log import logger
from auto_evacuates.openstack_novaclient import NovaClientObj as nova_client
from auto_evacuates.fence_agent import Fence
from auto_evacuates.fence_agent import FENCE_NODES

eventlet.monkey_patch()
FENCE_NODE = FENCE_NODES


class NovaService(object):

    def __init__(self):
        self.service, self.compute = nova_client.get_compute()

    def sys_compute(self, compute):
        """Use eventlet spawn call compute_check get
           opoenstack-nova-compute service status
        return: sys_com data format list
        """
        logger.info("openstack-nova-compute service start check")
        sys_com = []

        def compute_check(ip):
            """ Use eventlet timeout config, When compute shutdown or
                mgmt network has error
            """
            with eventlet.Timeout(5, False):
                (s, o) = commands.getstatusoutput("ssh '%s' systemctl -a|grep "
                                                  "openstack-nova-compute"
                                                  % ip)
            if s == 0 and o is not None:
                if 'running' in o and 'active' in o:
                    sys_com.append({"node": ip, "status": "up",
                                    "datatype": "novacompute"})
                elif 'dead' in o and 'inactive' in o:
                    sys_com.append({"node": ip, "status": "down",
                                    "datatype": "novacompute"})
                elif 'failed' in o:
                    sys_com.append({"node": ip, "status": "down",
                                    "datatype": "novacompute"})
            else:
                sys_com.append({"node": ip, "status": "unknown",
                                "datatype": "novacompute"})
                logger.warn("%s openstack-nova-compute service unknown" % ip)

        # use eventlet create green pool, use pool call function
        pool = eventlet.GreenPool()
        for ip in compute:
            pool.spawn(compute_check, ip)
        pool.waitall()

        return sys_com

    def ser_compute(self):
        """use novaclient check nova-compute status and state message

        novaclient get state all ways  time delay
        :return: ser_com data format list
        """
        logger.info("nova-compute status and state start check")

        ser_com = []
        services = self.service
        if not services:
            logger.warn("Service could not be found nova-compute")
        else:
            count = len(services)
            counter = 0
            while counter < count:
                service = services[counter]
                host = service.host
                if service.status == "enabled" and service.state == "up":
                    ser_com.append({"node": host, "status": "up",
                                    "datatype": "novaservice"})
                elif service.status == "disabled":
                    if service.disabled_reason:
                        ser_com.append({"node": host, "status": "up",
                                        "datatype": "novaservice"})
                    ser_com.append({"node": host, "status": "down",
                                    "datatype": "novaservice"})
                elif service.state == "down":
                    ser_com.append({"node": host, "status": "down",
                                    "datatype": "novaservice"})
                else:
                    logger.error("nova compute on host %s is in an "
                                 "unknown State" % (service.host))
                counter += 1

            return ser_com


class ServiceManage(object):
    """Use Service Manage all nova service  operation"""

    def __init__(self):
        # call NovaService class, check nova service status and
        # nova compute status
        self.ns = NovaService()

    def get_service_status(self):
        """ When manage get nova service check data ,will be return nova_status data

        :return: nova_status is a list data
        :Example: nova_status = [{"node":"node-1", "status":"up",
        "datatype":"novaservice"}, {"node":"node-2", "status":"down",
        "datatype":"novacompute"}]
        """

        nova_status = []
        for i in self.ns.sys_compute(self.ns.compute):
            nova_status.append(i)

        for n in self.ns.ser_compute():
            nova_status.append(n)

        return nova_status

    def service_retry(self, node, datatype):
        """If first check false, the check will retry three times

        """
        compute = []
        compute.append(node)
        role = "service"

        for i in range(3):
            logger.warn("%s %s start retry %d check" % (node, datatype, i+1))
            if datatype == "novaservice":
                status = self.ns.ser_compute()
            else:
                status = self.ns.sys_compute(compute)

            for n in status:
                if node in n.values() and 'up' in n.values():
                    # when retry, the node ser_compute service auto recovery,
                    # set count = retry_count
                    return True
            time.sleep(10)
        # Execute three times after, function not return, will be execute fence
        fence = Fence()
        fence.compute_fence(role, node, datatype)
