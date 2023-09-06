from ICNProtocol import ICNProtocol
from Sensor import Sensor, TempSensor, PerSensor, HumSensor, BarSensor, CloudSensor, SnowSensor, WaterSensor, WindSensor
from twisted.internet import reactor
from Tlru import TLRU_Table
import logging
import argparse
from time import time, sleep
from threading import Thread


class Node:

    def __init__(self, node_id=None, port=None, data_n=None, data_v=None):
        self.name = node_id
        self.PIT = TLRU_Table(3)
        self.cache = TLRU_Table(3)
        self.locations = TLRU_Table(3)
        self.peers = []
        self.data = {}
        self.sensors = {}

        self.icn = ICNProtocol(self, self.name, port)

        if data_n is not None:
            # Temperature sensor with a time to use of 60 (since it updates once per min)
            self.sensors[data_n+"_temp"] = TempSensor(data_n, 60)
            self.sensors[data_n+"_temp"].update()
            self.data[data_n+"_temp"] = self.sensors[data_n+"_temp"].getValue()

            self.sensors[data_n+"_per"] = PerSensor(data_n, 60)
            self.sensors[data_n+"_per"].update()
            self.data[data_n+"_per"] = self.sensors[data_n+"_per"].getValue()

            self.sensors[data_n+"_hum"] = HumSensor(data_n, 60)
            self.sensors[data_n+"_hum"].update()
            self.data[data_n+"_hum"] = self.sensors[data_n+"_hum"].getValue()

            self.sensors[data_n+"_bar"] = BarSensor(data_n, 60)
            self.sensors[data_n+"_bar"].update()
            self.data[data_n+"_bar"] = self.sensors[data_n+"_bar"].getValue()

            self.sensors[data_n+"_cloud"] = CloudSensor(data_n, 60)
            self.sensors[data_n+"_cloud"].update()
            self.data[data_n+"_cloud"] = self.sensors[data_n+"_cloud"].getValue()

            self.sensors[data_n+"_snow"] = SnowSensor(data_n, 60)
            self.sensors[data_n+"_snow"].update()
            self.data[data_n+"_snow"] = self.sensors[data_n+"_snow"].getValue()

            self.sensors[data_n+"_water"] = WaterSensor(data_n, 60)
            self.sensors[data_n+"_water"].update()
            self.data[data_n+"_water"] = self.sensors[data_n+"_water"].getValue()

            self.sensors[data_n+"_wind"] = WindSensor(data_n, 60)
            self.sensors[data_n+"_wind"].update()
            self.data[data_n+"_wind"] = self.sensors[data_n+"_wind"].getValue()


        th = Thread(target=self.updateData, daemon=True)
        th.start()

    def addToPIT(self, data_name, node_name, ttw, count=1):
        self.PIT.add(data_name, node_name, ttw, count)

    def removeCountFromPIT(self, data_name):
        dest, count = self.PIT.removeCount(data_name)
        return dest, count

    def removeFromPIT(self, data_name):
        dest, count = self.PIT.remove(data_name)
        return dest, count

    def hasPITEntry(self, data_name):
        return self.PIT.contains(data_name)

    def canRequestFrom(self, node_name):
        for d in self.PIT:
            print(d)
            if d in self.locations:
                if self.locations[d] == node_name:
                    v, t = self.PIT.get(d)
                    return True, d, v, t
        return False, None, None, None

    def hasLocation(self, data_name):
        if self.locations.contains(data_name):
            return True
        else:
            return False

    def addLocation(self, data_name, location):
        self.locations.add(data_name, location)

    def removeLocation(self, data_name):
        dest, count = self.locations.remove(data_name)
        return dest, count

    def getLocation(self, data_name):
        location, t = self.locations.get(data_name)
        return location

    def cacheData(self, data_name, data_val, ttu):
        self.cache.add(data_name, data_val, ttu)

    def hasCache(self, data_name):
        if self.cache.contains(data_name):
            return True
        else:
            return False

    def getCache(self, data_name):
        data, ttu = self.cache.get(data_name)
        return data, ttu

    def addPeer(self, node_name):
        if node_name not in self.peers:
            self.peers.append(node_name)

    def removePeer(self, node_name):
        if node_name in self.peers:
            self.peers.remove(node_name)

    def hasData(self, data_name):
        if data_name in self.data:
            return True
        else:
            return False

    def run(self):
        self.reactor = reactor
        self.reactor.run()

    def getData(self, data_name):
        if data_name in self.data:
            data_val, ttu = self.data[data_name]
            ttu += time()
            return data_val, ttu
        else:
            return None

    def requestData(self, data_name, ttw=10):
        ttw += time()
        self.icn.requestData(data_name, ttw)

    def useData(self, data_name, data_val):
        logging.info(f"Received {data_name} with a value of {data_val}")

    # Update data sources loop
    def updateData(self):
        while True:
            for k, s in self.sensors.items():
                s.update()
                self.data[k] = s.getValue()
            sleep(10)

    def __str__(self):
        str = f"Name: {self.name}\nPIT:\n{self.PIT}\nCache:\n{self.cache}\nLocations:\n{self.locations}\nPeers:\n{self.peers}\n"
        str += f"Data:\n{self.data}\nIP map:\n{self.icn.ip_node.IP_map}\nConnections:\n{self.icn.ip_node.connections}\nFallback:"
        return str + f"\n{self.icn.ip_node.fallback_address}\nFallbacks:\n{self.icn.ip_node.fallbacks}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node-name', help='Name for node in this network', type=str)
    parser.add_argument('--port', help='Port for this node', type=int, default=5789)
    parser.add_argument('--data-n', help='Data name for this node', type=str, default=None)
    parser.add_argument('--data-v', help='Data for the node', type=str, default="10")
    parser.add_argument('--logging-level', help='Logging level: 10 - Debug, 20 - Info, 30 - Warnings', type=int, default=20)
    args = parser.parse_args()

    if args.node_name is None:
        print("Please specify a node name")
        exit(1)

    if args.port is None:
        print("Please specify the port for this node")
        exit(1)

    logging.basicConfig(level=args.logging_level, format='{0:8}%(levelname)-8s %(message)s'.format(args.node_name + ':'))
    logging.debug(f"Running node {args.node_name}")
    n = Node(args.node_name, args.port, args.data_n, args.data_v)
    n.run()


if __name__ == "__main__":
    main()
