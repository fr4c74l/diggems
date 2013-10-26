import random
import radix64

true_random = random.SystemRandom()

def gen_token():
    return radix64.encode(true_random.getrandbits(132))
