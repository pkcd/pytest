def bubblesort(int_array_seq, int_length):
    i = 0
    while i < int_length and int_array_seq[i] > 0 and int_length > 1:
        j = 0
        while j < int_length:
            if int_array_seq[j] > int_array_seq[j+1]:
                k = int_array_seq[j]
                int_array_seq[j] = int_array_seq[j + 1]
                int_array_seq[j + 1] = k
            j = j + 1
        i = i + 1