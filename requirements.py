import subprocess


def save_requirements():
    try:
        # Выполнение команды pip freeze и запись в файл requirements.txt
        subprocess.run(["pip", "freeze", ">", "requirements.txt"], shell=True, check=True)
        print("Файл requirements.txt успешно создан.")
    except subprocess.CalledProcessError as e:
        print(f"Произошла ошибка: {e}")


def install_requirements():
    try:
        # Выполнение команды pip freeze и запись в файл requirements.txt
        print("Устанавливаю зависимости из requirements.txt")
        subprocess.run(["pip", "install ", "-r", "requirements.txt"], shell=True, check=True)
        print("Зависимости из requirements.txt установлены")
    except subprocess.CalledProcessError as e:
        print(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    save_requirements()
    # install_requirements()