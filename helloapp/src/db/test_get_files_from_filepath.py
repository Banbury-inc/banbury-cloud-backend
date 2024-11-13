from .get_files_from_filepath import get_files_from_filepath

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

if __name__ == "__main__":
    test_get_files_from_filepath()