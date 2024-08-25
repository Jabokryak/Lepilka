
Лепилка позволяет объединять и накладывать аудио фрагменты.
Для запуска программы должен быть установлен Python. Также необходимо скачать ffmpeg (https://ffmpeg.org/download.html) - набор библиотек для обработки звука, эти быблиотеки использует библиотека pudub Питона.
Скаченные файлы ffmpeg.exe и ffprobe.exe можно положить в папку ffmpeg, расположенную в той же папке, что и скрипт lepilka.py (путь этой папки добавляется в Path в файле lepilka.bat). Либо добавить путь до этих файлов в переменную окружения Path.
Порядок наложения и объединения аудио фрагментов задаётся в виде json-файла, путь к котрому передаётся в качестве параметра скрипту.
Команды, которые поддерживает скрипт:
<code>
1. Добавление фрагмента
  {"method": "add"
  ,"file": "Фоновая/Crazy Frog.mp3"  - путь к файлу с наименованием (в данном случае путь относительный от папки откуда запущен скрипт)
  ,"start_second": 20                - начиная с какой секунды будет взыт фрагмент из файла
  ,"duration": 5}                    - продолжительность фрагмента, сек.
2. Тишина
  {"method": "add"
  ,"silence": true
  ,"duration": 1}                    - продолжительность тишины, сек.
3. Наложение фрагмента 
  {"method": "overlay"
  ,"file": "Бипы/beep_bass.wav"
  ,"song_gain": -8                   - изменение громкости дБ исходного фрагмента. Позволяет сделать исходный фрагмент тише при наложении фрагмента.
  ,"position": -10                   - с какой секунды исходного фрагмента будет наложен фрагмент
  ,"times": 2                        - сколько раз подряд будет наложен фрагмент
  ,"vol": 50}                        - регулировка громкости фрагмента
4. Цикл по файлам из папки import_folder, удовлетворяющим маске file_mask
  {"method": "foreach"
  ,"import_folder": "Оригиналы"
  ,"export_folder": "Результат %Y%m%d/"  - папка экспорта для каждой итерации цикла. Поддерживает вывод текущей даты и времени.
  ,"file_mask": ".+(mp3|wav)$"
  ,"do": [...]}                      - массив команд, выполняемых в каждой итерации
5. Экспорт
  {"method": "export"
  "file": ""Результат %Y%m%d/ %H%M%S"}  - папка экспорта. Если есть родительский "method": "foreach", то путь экспорта берётся из его поля "export_folder". Поддерживает вывод текущей даты и времени.
</code>
Для запуска скрипта удобно использовать файл lepilka.bat, который прописывет путь до библиотек ffmpeg, запускает скрипт lepilka.py и передаёт ему json-файл с командами.
