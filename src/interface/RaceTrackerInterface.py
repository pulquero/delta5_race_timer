'''RaceTracker interface layer.'''

from Node import Node
from BaseHardwareInterface import BaseHardwareInterface
import json
import websocket
import threading
from Queue import Queue
from Queue import Empty

class RaceTrackerInterface(BaseHardwareInterface):
    def __init__(self, Config):
        BaseHardwareInterface.__init__(self)
        self.update_thread = None # Thread for running the main update loop
        self.pass_record_callback = None # Function added in server.py
        self.hardware_log_callback = None # Function added in server.py
        self.new_enter_or_exit_at_callback = None # Function added in server.py
        self.node_crossing_callback = None # Function added in server.py

        self.nodes = []

        appAddress = Config['RACETRACKER']['ADDRESS']
        print 'Connecting to {0}'.format(appAddress)

        self.ws_msg_queue = Queue()

        def ws_on_open(ws):
	        ws.send('get_settings')
		
        def ws_on_message(ws, message):
        	msg = json.loads(message)
        	if 'notification' in msg:
        		notif = msg['notification']
        		data = msg['data']
        		if notif == 'heartbeat':
        			self.handle_heartbeat(data)
        		elif notif == 'pass_record':
        			self.handle_pass_record(data)
        	else:
	        	self.ws_msg_queue.put(msg)

       	def ws_on_error(ws, error):
       		print error

        self.ws = websocket.WebSocketApp('ws://{0}:5001/'.format(appAddress),
        	on_open = ws_on_open,
        	on_message = ws_on_message,
        	on_error = ws_on_error)
        thread = threading.Thread(target=self.ws.run_forever)
        thread.setDaemon(True)
        thread.start()

        settings = self.ws_wait_for_response()

        for index, n in enumerate(settings['nodes']):
			node = Node()
			node.index = index
			node.frequency = n['frequency']
			self.nodes.append(node)

    def ws_wait_for_response(self):
        return self.ws_msg_queue.get(True, 5*60)

    def handle_heartbeat(self, data):
    	rssi = data['current_rssi']
    	for index, value in enumerate(rssi):
    		self.nodes[index].current_rssi = value

    def handle_pass_record(self, data):
    	nodeIndex = data['node']
    	node = self.nodes[nodeIndex]
    	node.lap_ms_since_start = data['timestamp']
    	self.pass_record_callback(node, 0)


    #
    # Update Loop
    #

    def start(self):
    	'''No-op'''

    #
    # External functions for setting data
    #

    def set_frequency(self, node_index, frequency):
        node = self.nodes[node_index]
        if frequency == None:
        	frequency = 0
        node.frequency = frequency
        settings = {}
        settings['node'] = node_index
        settings['frequency'] = frequency
        self.ws.send(json.dumps(settings))

    def set_calibration_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def enable_calibration_mode(self):
        pass  # dummy function; no longer supported

    def set_calibration_offset_global(self, offset):
        return offset  # dummy function; no longer supported

    def set_trigger_threshold_global(self, threshold):
        return threshold  # dummy function; no longer supported

    def set_filter_ratio(self, node_index, filter_ratio):
        node = self.nodes[node_index]

    def set_filter_ratio_global(self, filter_ratio):
        self.filter_ratio = filter_ratio
        for node in self.nodes:
            self.set_filter_ratio(node.index, filter_ratio)
        return self.filter_ratio

    def set_history_expire_global(self, history_expire_duration):
        settings = {}
        settings['minimum_lap_time'] = history_expire_duration/1000
        self.ws.send(json.dumps(settings))

    def mark_start_time_global(self):
    	start = {}
    	start['node'] = -1
    	self.ws.send(json.dumps(start))

    def get_catch_history(self, node_index):
    	return None


def get_hardware_interface(Config):
    '''Returns the RaceTracker interface object.'''
    return RaceTrackerInterface(Config)
