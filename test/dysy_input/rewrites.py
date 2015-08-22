def rewrites(int_a, int_b, int_array_seq, int_length):
    x = int_a
    y = -1
    while x < int_length and int_array_seq[x] > -1 and int_array_seq[x] > y:
        y = int_array_seq[x]
        if int_array_seq[x] == int_b and int_b < int_length:
            int_array_seq[int_b] = x
        x = x + 1
    print int_array_seq