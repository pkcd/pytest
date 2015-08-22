def remainder(int_a, int_b):
    r = 0-1
    cy = 0
    ny = 0

    if int_a!=0:
        if (int_b!=0):
            if (int_a>0):
                if (int_b>0):
                    while((int_a-ny)>=int_b):
                        ny=ny+int_b
                        r=int_a-ny
                        cy=cy+1
                else: # int_b<0
                    while ((int_b>=0) and (int_a+ny)>= int_b) or ((not int_b>=0) and (int_a+ny)>= -int_b):
                        ny=ny+int_b
                        r=int_a+ny
                        cy=cy-1

            else: # int_a<0
                if int_b>0:
                    while ((int_a+ny)>=0 and (int_a+ny)>=int_b) or ((not (int_a+ny)>=0) and -(int_a+ny)>=int_b):
                        ny=ny+int_b
                        r=int_a+ny
                        cy=cy-1
                else:
                    while int_b>=(int_a-ny):
                        ny=ny+int_b
                        if (int_a-ny)>=0:
                            r = int_a-ny
                        else:
                            r = -(int_a-ny)
                        cy=cy+1

    return r