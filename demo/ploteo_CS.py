#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para plotear los resultados de las pruebas para CS (Credenciales Simples)

@author: rafa
"""

import re
import subprocess
import os
from turtle import title
import pandas as pd
import matplotlib.pyplot as plt
import psutil as ps
import asyncio

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
'''
data = {}
data["Startup"] = tiempos_startup
data["Connect"] = tiempos_connect
data["Publish"] = tiempos_publish
data["Average per credential"] = tiempos_avg_credential
data["Average per proof"] = tiempos_avg_proof
data["Total runtime"] = tiempos_total


#print(data)
#En index poner las credenciales que haya puesto
credenciales_string = []
for credentials in credenciales:
    credenciales_string.append(str(credentials))
    
#Creo el dataframe para mostrarlo
frame = pd.DataFrame(tiempos_startup, index = range(1,pruebas + 1), columns= ["Startup duration"])
frame.name = "Startup duration"
print(frame.to_string())
frame.corr()
frame = frame.astype(float)
'''

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
    #cpu = cpu_array[cred-1]
    #ram = ram_array[cred-1]
    dataframe = pd.DataFrame({
        'Startup': startup,
        'Connect': connect,
        'Publish': publish,
        'Average cred': avg_credential,
        'Average proof': avg_proof,
        'Total': total,
        #'CPU': cpu,
        #'RAM': ram
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







#frame.plot()

#plt.xlabel('Número de credenciales')
#plt.ylabel('Tiempo (s)')
#plt.title("Startup duration")
#plt.show()

'''frame['Connect'].plot()

plt.xlabel('Número de credenciales')
plt.ylabel('Tiempo (s)')
plt.title("Connect duration")
plt.show()

frame['Publish'].plot()

plt.xlabel('Número de credenciales')
plt.ylabel('Tiempo (s)')
plt.title("Publish duration")
plt.show()

frame['Average per credential'].plot()

plt.xlabel('Número de credenciales')
plt.ylabel('Tiempo (s)')
plt.title("Average time per credential")
plt.show()

frame['Average per proof'].plot()

plt.xlabel('Número de credenciales')
plt.ylabel('Tiempo (s)')
plt.title("Average time per proof")
plt.show()

frame['Total runtime'].plot()

plt.xlabel('Número de credenciales')
plt.ylabel('Tiempo (s)')
plt.title("Total runtime")
plt.show()

#print(f'El porcentaje de CPU usado es {ps.cpu_percent()}')
#print(f'El porcentaje de RAM usado es {ps.virtual_memory()[2]}')
''' 
'''      
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Script para monitorizar el rendimiento de un modelo SSI"
    )
    parser.add_argument(
        "--multitenant", action="store_true", help="Enable multitenancy options"
    )
    parser.add_argument(
        "--mediation", action="store_true", help="Enable mediation functionality"
    )
    parser.add_argument(
        "--revocation", action="store_true", help="Enable credential revocation"
    )
    parser.add_argument(
        "--revoke_credentials", action="store_true", help="Revoke the credentials issued"
    )
    parser.add_argument(
        "--multi-ledger",
        action="store_true",
        help=(
            "Enable multiple ledger mode, config file can be found "
            "here: ./demo/multi_ledger_config.yml"
        ),
    )
    parser.add_argument(
        "--proof_presentation", action="store_true", help="Enable proof presentation"
    )
    parser.add_argument(
        "--publish_revocations_at_once", action="store_true", help="Publish revocations in only one transaction"
    )
    parser.add_argument(
        "--tails-server-base-url",
        type=str,
        metavar="<tails-server-base-url>",
        help="Tails server base url",
    )
    args = parser.parse_args()

    #inicializa la url del servidor tails
    tails_server_base_url = args.tails_server_base_url or os.getenv("PUBLIC_TAILS_URL")

    #recuerda especificar la url del servidor en caso de no haberlo hecho
    if args.revocation and not tails_server_base_url:
        raise Exception(
            "If revocation is enabled, --tails-server-base-url must be provided"
        )

    try:
        asyncio.get_event_loop().run_until_complete(
            main(
                args.multitenant,
                args.mediation,
                args.multi_ledger,
                args.revocation,
                args.proof_presentation,
                args.revoke_credentials,
                args.publish_revocations_at_once,
            )
        )
    except KeyboardInterrupt:
        os._exit(1)
'''
