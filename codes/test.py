from PIL import Image

for p in ["D:\\py_workplace\\table_pet\\pictures\\finally\\sleeping.png",
          "D:\\py_workplace\\table_pet\\pictures\\finally\\speaking.png",
          "D:\\py_workplace\\table_pet\\pictures\\finally\\standby.png"]:
    img = Image.open(p)
    print(p, img.mode)