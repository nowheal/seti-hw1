from solution import QuestRunner


if __name__ == "__main__":
    # Ручное формирование HTTP-пакетов через сокеты
     QuestRunner.run_raw_sockets()

    # Через библиотеку requests (8 баллов)
    # QuestRunner.run_requests_lib()
