from .get_files_from_filepath import get_files_from_filepath
import time

def test_get_files_from_filepath():

    #username = "mmills"
    #filepath = "/home/mmills/BCloud/IMG_0099.JPG"
    #result = get_files_from_filepath(username, filepath)
    #print(result)


    #filepath = "/home/mmills/BCloud/"
    username = "mmills"
    filepath = "Core/Devices/michael-ubuntu"
    result = get_files_from_filepath(username, filepath)
    print(result)



def test_time_to_get_files_from_filepath():
    
    username = "mmills"
    filepath = "Core/Devices/michael-ubuntu"
    
    start_time = time.time()
    result = get_files_from_filepath(username, filepath)
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.4f} seconds")


def main():
    #test_get_files_from_filepath()
    test_time_to_get_files_from_filepath()

if __name__ == "__main__":
    main()