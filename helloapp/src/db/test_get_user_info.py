from .get_user_info import get_user_info
import time

def test_get_user_info():

    #username = "mmills"
    #filepath = "/home/mmills/BCloud/IMG_0099.JPG"
    #result = get_files_from_filepath(username, filepath)
    #print(result)


    #filepath = "/home/mmills/BCloud/"
    username = "mmills"
    result = get_user_info(username)
    print(result)



def test_time_to_get_user_info():
    
    username = "mmills"
    
    start_time = time.time()
    result = get_user_info(username)
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    print(result)


def main():
    #test_get_user_info()
    test_time_to_get_user_info()

if __name__ == "__main__":
    main()