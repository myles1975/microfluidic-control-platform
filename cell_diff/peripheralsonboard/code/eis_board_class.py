# eis board class
# sends commands to control frequency board to server


class Eis_Board:
    
    # initialized Eis_Board class
    def __init__(self, client):
        self.client = client
    
    # sends command to put device in single frequeny mode
    def single_frequency(self):
        self.client.send("single_freq_mode*".encode())
    
    # sends command to start frequency sweep
    def start_frequency(self):
        self.client.send("start_freq_t*".encode())
    
    # sends command to stop frequenct sweep 
    def stop_frequency(self):
        self.client.send("stop_freq*".encode())
        
    # sends frequency value
    def set_freq(self, val):
        self.client.send(('start*').encode())
        self.client.send((str(val) + "*").encode())