import board
import pwmio
# print( dir(board))


if __name__ == '__main__':

	# available pins are D12, D18, D13, D19
	pin18 = pwmio.PWMOut(board.D18)
	pin18.duty_cycle = 2**15 # 50%
	pin18.frequency = 1000

	
