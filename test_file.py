import h5py
import sys

def create_newfile(file_dir:'str')
    newfile=h5py.File(file_dir,'w')
    for i in dat.keys():
        try:
            print(dat[i].keys)
            newfile.create_group(i)
            for ii in dat[i].keys():
                try:
                    print(dat[i][ii].keys())
                    newfile.create_group(f'{i}/{ii}')
                    for iii in dat[i][ii].keys():
                        print(f'writing in {i}/{ii}/{iii}')
                        newfile.create_dataset(f'{i}/{ii}/{iii}',1,dtype='i', data=0)
                except:
                    print(f'writing in {i}/{ii}')
                    newfile.create_dataset(f'{i}/{ii}',(5,5), dtype='f',data=np.random.rand(5,5))
        except:
            newfile.create_dataset(i,1, dtype='i') 
    for ints in dat['intg'].keys():
        try:
            for ints_i in dat[f'intg/{ints}'].keys():
                print(f'printing {ints_i}')
                newfile.create_dataset(f'intg/{ints}/{ints_i}',1,dtype='i', data=0)
                #except:
                #    print(f'no data in intg/{ints}/{ints_i}')
        except:
            newfile.create_dataset(f'intg/{ints}s',1,dtype='i', data=0)