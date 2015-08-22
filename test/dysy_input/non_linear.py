def non_linear(real_a, real_b):
    if real_a < 1000:
        return False
    if real_b < 1000:
        return False
    if (real_a + real_b)**2 - 1230000000 < 1e-10:
        return True
    else:
        return False