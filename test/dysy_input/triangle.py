def triangle2(int_a, int_b, int_c):
    if int_a<=0 or int_b<=0 or int_c<=0:
            return 1 # was 4
    tmp = 0

    if int_a==int_b:
        tmp = tmp + 1

    if int_a==int_c:
        tmp = tmp + 2

    if int_b==int_c:
        tmp = tmp + 3

    if tmp == 0:
        if (int_a+int_b<=int_c) or (int_b+int_c <=int_a) or (int_a+int_c<=int_b):
            tmp = 1 # was 4
        else:
            tmp = 2 # was 1
        return tmp

    if tmp > 3:
        tmp = 4 #  was 3;
    elif tmp==1 and (int_a+int_b>int_c):
        tmp = 3 #  was 2
    elif tmp==2 and (int_a+int_c>int_b):
        tmp = 3 #  was 2
    elif tmp==3 and (int_b+int_c>int_a):
        tmp = 3 #  was 2
    else:
        tmp = 1; #  was 4

    return tmp;