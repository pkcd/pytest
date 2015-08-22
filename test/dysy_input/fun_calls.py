def fun_calls(real_a_seq, real_b_seq):
    i = 0
    x = 0.0
    while i < min(len(real_a_seq), len(real_b_seq)):
        if real_a_seq[i] > x:
            x = real_a_seq[i]
            if not(real_a_seq[i] * 2 == real_b_seq[i]):
                return False
        else:
            return False
        i = i + 1
    return True