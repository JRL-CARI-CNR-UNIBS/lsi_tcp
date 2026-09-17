# 1. Installazione

## 1.1. Programmi da installare

In Windows,
- Seguire le istruzioni per installare Git [Git](https://git-scm.com/install/windows)
- Scaricare [Anaconda](https://anaconda.com/api/installers/Miniconda3-latest-Windows-x86_64.exe) e installare il programma.

## 1.2. Clonare / installare il pacchetto

- Scegliere una cartella di lavoro (ad esempio: C:\Users\beschi\Documents\lsa)
- Aprire _Anaconda Powershell Prompt_
- impostare la cartella di lavoro (mettete il percorso giusto!)
  ```bash
  cd "C:\Users\beschi\Documents\lsa"
  ```
- Scaricare il programma digitando il comando:
  ```bash
  git clone https://github.com/JRL-CARI-CNR-UNIBS/lsi_tcp
  ```
- Creare l'ambiente e installare le dipendenze
  ```bash
  conda create -n lsa python=3.11
  conda activate lsa
  cd lsi_tcp
  pip install -e .
  ```
- Testare il programma eseguendo
  ```bash
  python example_proportional.py --fake
  ```
- Aprire la pagina del browser all'indirizzo [http://127.0.0.1:8051/](http://127.0.0.1:8051/)
  
> **Nota**: il pacchetto è pensato per Python ≥ 3.11 .

## 1.3. Connessione

La connessione del dispositivo è descritta nella foto
![connessione.png](../connessione.png)
e a questo [link](https://jckantor.github.io/cbe30338-book/tclab/00.01-setting-up-tclab.html).

> [!WARNING]
> Gli heater possono essere molto caldi, non toccateli!
