#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para plotear los resultados de las pruebas para CS (Credenciales Simples)

@author: rafa
"""

import re
import subprocess
import os
import pandas as pd
import matplotlib.pyplot as plt



#Vector de vectores (cred X pruebas)
tiempos_startup = []
tiempos_connect = []
tiempos_publish = []
tiempos_avg_credential = []
tiempos_avg_proof = []
tiempos_total = []
cpu_array = []
ram_array = []
pid = os.getpid()

credenciales = [10, 20, 50, 100, 150, 200, 250, 300, 400, 500]
pruebas = 25

for cred in credenciales:
    tiempos_startup_p = []
    tiempos_connect_p = []
    tiempos_publish_p = []
    tiempos_avg_credential_p = []
    tiempos_avg_proof_p = []
    tiempos_total_p = []
    tiempos_revoke_p = []
    ram_p = []
    cpu_p = []
    for prueba in range(1,pruebas+1):
        
        with open(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CS/{cred}_credenciales/prueba{prueba}_con_{cred}_credenciales.txt","r") as file:
            for line in file:
                if re.search("Startup duration:",line):
                    primero = line.index(":")
                    segundo = line.index("s")
                    tiempos_startup_p.append(float(line[primero+2:segundo]))
                elif re.search("Connect duration:",line):
                    primero = line.index(":")
                    segundo = line.index("s")
                    tiempos_connect_p.append(float(line[primero+2:segundo]))
                elif re.search("Publish duration:",line):
                    primero = line.index(":")
                    segundo = line.index("s", 26)
                    tiempos_publish_p.append(float(line[primero+2:segundo]))
                elif re.search("Average time per credential:",line):
                    primero = line.index(":")
                    segundo = line.index("s")
                    tiempos_avg_credential_p.append(float(line[primero+2:segundo]))
                elif re.search("Average time per proofs:",line):
                    primero = line.index(":")
                    segundo = line.index("s", 60)
                    tiempos_avg_proof_p.append(float(line[primero+2:segundo]))
                elif re.search("Total runtime:",line):
                    primero = line.index(":")
                    segundo = line.index("s")
                    tiempos_total_p.append(float(line[primero+2:segundo]))
        
        with open(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CS/{cred}_credenciales/datosCPUyRAM/CPU_{cred}_credenciales_prueba_{prueba}.txt","r") as file:
            total_cpu = 0
            total_ram = 0
            contador = 0
            for line in file:
                total_cpu = total_cpu + float(line[41:45])
                total_ram = total_ram + float(line[46:50])
                contador = contador + 1
                
            cpu_p.append(total_cpu/contador)
            ram_p.append(total_ram/contador)
        
        
    while(len(tiempos_startup_p) != pruebas):
        tiempos_startup_p.append(sum(tiempos_startup_p)/len(tiempos_startup_p))
    while(len(tiempos_publish_p) != pruebas):
        tiempos_publish_p.append(sum(tiempos_publish_p)/len(tiempos_publish_p))
    while(len(tiempos_connect_p) != pruebas):
        tiempos_connect_p.append(sum(tiempos_connect_p)/len(tiempos_connect_p))
    while(len(tiempos_avg_credential_p) != pruebas):
        tiempos_avg_credential_p.append(sum(tiempos_avg_credential_p)/len(tiempos_avg_credential_p))
    while(len(tiempos_avg_proof_p) != pruebas):
        tiempos_avg_proof_p.append(sum(tiempos_avg_proof_p)/len(tiempos_avg_proof_p))
    while(len(tiempos_total_p) != pruebas):
        tiempos_total_p.append(sum(tiempos_total_p)/len(tiempos_total_p))
    
    tiempos_startup.append(tiempos_startup_p)
    tiempos_connect.append(tiempos_connect_p)
    tiempos_publish.append(tiempos_publish_p)
    tiempos_avg_credential.append(tiempos_avg_credential_p)
    tiempos_avg_proof.append(tiempos_avg_proof_p)
    tiempos_total.append(tiempos_total_p)
    #cpu_array.append(cpu_p)
    #ram_array.append(ram_p)

#Paso a DataFrame de pandas para tener una tabla


#Voy a tener 25 pruebas para cada credencial. Entonces voy a tener 10 gráficas de Scatter donde lo suyo sería ver la media, la desviación
#típica y eso. Después haré un dataframe con las medias de estas sietes gráficas. A este nuevo dataframe lo muestro para ver como se comporta
#todo conforme subo el número de credenciales.
#Ploteo cada una de las columnas del dataFrame

medias_startup = []
medias_connect = []
medias_publish = []
medias_avg_credential = []
medias_avg_proof = []
medias_total = []

credenciales_string = []
for credentials in credenciales:
    credenciales_string.append(str(credentials))

for cred in range(1, len(credenciales)+1):
    dataframe = None
    startup = tiempos_startup[cred-1]
    connect = tiempos_connect[cred-1]
    publish = tiempos_publish[cred-1]
    avg_credential = tiempos_avg_credential[cred-1]
    avg_proof = tiempos_avg_proof[cred-1]
    total = tiempos_total[cred-1]
    cpu = cpu_array[cred-1]
    ram = ram_array[cred-1]
    dataframe = pd.DataFrame({
        'Startup': startup,
        'Connect': connect,
        'Publish': publish,
        'Average cred': avg_credential,
        'Average proof': avg_proof,
        'Total': total,
        'CPU': cpu,
        'RAM': ram
        })
    #dataframe.index = credenciales_string
    dataframe = dataframe.astype(float)
    print(f"Datos estadísticos para {credenciales[cred-1]} credenciales \n")
    print(dataframe.describe())
    print("\n")
    dataframe.plot(kind='box', title=f"Pruebas para {credenciales[cred-1]} credenciales")
    medias_startup.append(dataframe["Startup"].mean())
    medias_connect.append(dataframe["Connect"].mean())
    medias_publish.append(dataframe["Publish"].mean())
    medias_avg_credential.append(dataframe["Average cred"].mean())
    medias_avg_proof.append(dataframe["Average proof"].mean())
    medias_total.append(dataframe["Total"].mean())

df_final = pd.DataFrame({
        'Startup': medias_startup,
        'Connect': medias_connect,
        'Publish': medias_publish,
        'Average cred': medias_avg_credential,
        'Average proof': medias_avg_proof,
        'Total': medias_total,
}, index = credenciales_string)
print(f"TABLA FINAL \n")
print(df_final)
plt.show()
df_final["Startup"].plot(title="FINAL Startup")
plt.show()

