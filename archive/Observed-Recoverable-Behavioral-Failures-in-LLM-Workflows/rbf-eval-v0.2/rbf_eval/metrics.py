import math

def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'), float('nan'))
    phat=k/n
    denom=1+z*z/n
    center=(phat+z*z/(2*n))/denom
    half=z*math.sqrt((phat*(1-phat)+z*z/(4*n))/n)/denom
    return max(0,center-half), min(1,center+half)
