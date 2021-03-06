
'''
AUTOR: RAFAEL ADAN LOPEZ.
FECHA: 20 DE JUNIO DE 2022

UNIVERSIDAD DE GRANADA
TRABAJO DE FIN DE GRADO: EVALUACION DE RENDIMIENTO DE ENTORNO SSI BASADO EN BLOCKCHAIN

SCRIPT PARA PLOTEAR LAS PRUEBAS GENERADAS CON EL SCRIPT PROOF_PRESENTATION_CR_NO_REVOCATION.PY

CAMBIAR LOS DIRECTORIOS PARA USO DEL SCRIPT, PUESTO QUE ESTA PUESTO LA RUTA DEL DESARROLLADOR.

'''

#Importación de librerías usadas
import re
import subprocess
import os
import pandas as pd
import matplotlib.pyplot as plt



#Vector de vectores donde se guardaran los tiempos y la CPU y RAM usada (cred X pruebas)
tiempos_startup = []
tiempos_connect = []
tiempos_publish = []
tiempos_avg_credential = []
tiempos_avg_proof = []
tiempos_total = []
cpu_array = []
ram_array = []
pid = os.getpid()

#Numero de credenciales y pruebas
credenciales = [10, 20, 50, 100, 150, 200, 250, 300, 400, 500]
pruebas = 25

for cred in credenciales:

    #Vector de tiempos con las 25 pruebas para una credencial
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
        
        #Se abre el archivo de log para la prueba 'prueba' y el numero de credencial 'cred' y se buscan los patrones para extraer los tiempos
        with open(f"/home/rafa/aca-py-performance/demo/pruebas/CR/sin_revocar/{cred}_credenciales/prueba{prueba}_con_{cred}_credenciales.txt","r") as file:
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

        #Se abre el archivo de log para la prueba 'prueba' y el numero de credencial 'cred' y se buscan los patrones para extraer la CPU y RAM usada
        with open(f"/home/rafa/aca-py-performance/demo/pruebas/CR/sin_revocar/{cred}_credenciales/datosCPUyRAM/CPU_{cred}_credenciales_prueba_{prueba}.txt","r") as file:
            total_cpu = 0
            total_ram = 0
            contador = 0
            for line in file:
                total_cpu = total_cpu + float(line[1:6])
                total_ram = total_ram + float(line[7:10])
                contador = contador + 1
                
            cpu_p.append(total_cpu/contador)
            ram_p.append(total_ram/contador)
        
    #En caso de que alguna prueba haya tenido errores, es posible que no haya tiempos. En ese caso, se rellena los elementos necesarios para llegar a 25 pruebas
    #con la media del vector
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
    
    #Se añade el vector de 25 pruebas para la credencial 'cred' al vector de vectores.
    tiempos_startup.append(tiempos_startup_p)
    tiempos_connect.append(tiempos_connect_p)
    tiempos_publish.append(tiempos_publish_p)
    tiempos_avg_credential.append(tiempos_avg_credential_p)
    tiempos_avg_proof.append(tiempos_avg_proof_p)
    tiempos_total.append(tiempos_total_p)
    cpu_array.append(cpu_p)
    ram_array.append(ram_p)

#Ploteo los tiempos tiempos en diagramas de cajas y bigotes para ver los datos estadísticos

datastartup = pd.DataFrame({
    '10 credenciales' : tiempos_startup[0],
    '20 credenciales' : tiempos_startup[1],
    '50 credenciales' : tiempos_startup[2],
    '100 credenciales': tiempos_startup[3],
    '150 credenciales': tiempos_startup[4],
    '200 credenciales': tiempos_startup[5],
    '250 credenciales': tiempos_startup[6],
    '300 credenciales': tiempos_startup[7],
    '400 credenciales': tiempos_startup[8],
    '500 credenciales': tiempos_startup[9],
})

datastartup.to_excel(f"tablas_excel/CR/sin_revocar/startup.xlsx")
datastartup.plot(kind='box', title=f"Startup CR no revocation", legend=True, xlabel="Numero de credenciales", ylabel = "Tiempo (s)")
plt.show()

dataconnect= pd.DataFrame({
    '10 credenciales' : tiempos_connect[0],
    '20 credenciales' : tiempos_connect[1],
    '50 credenciales' : tiempos_connect[2],
    '100 credenciales': tiempos_connect[3],
    '150 credenciales': tiempos_connect[4],
    '200 credenciales': tiempos_connect[5],
    '250 credenciales': tiempos_connect[6],
    '300 credenciales': tiempos_connect[7],
    '400 credenciales': tiempos_connect[8],
    '500 credenciales': tiempos_connect[9],
})

dataconnect.to_excel(f"tablas_excel/CR/sin_revocar/connect.xlsx")
dataconnect.plot(kind='box', title=f"Connect CR no revocation", legend=True, xlabel="Numero de credenciales", ylabel = "Tiempo (s)")
plt.show()

datapublish = pd.DataFrame({
    '10 credenciales' : tiempos_publish[0],
    '20 credenciales' : tiempos_publish[1],
    '50 credenciales' : tiempos_publish[2],
    '100 credenciales': tiempos_publish[3],
    '150 credenciales': tiempos_publish[4],
    '200 credenciales': tiempos_publish[5],
    '250 credenciales': tiempos_publish[6],
    '300 credenciales': tiempos_publish[7],
    '400 credenciales': tiempos_publish[8],
    '500 credenciales': tiempos_publish[9],
})

datapublish.to_excel(f"tablas_excel/CR/sin_revocar/publish.xlsx")
datapublish.plot(kind='box', title=f"Publish CR no revocation", legend=True, xlabel="Numero de credenciales", ylabel = "Tiempo (s)")
plt.show()

dataavgcred = pd.DataFrame({
    '10 credenciales' : tiempos_avg_credential[0],
    '20 credenciales' : tiempos_avg_credential[1],
    '50 credenciales' : tiempos_avg_credential[2],
    '100 credenciales': tiempos_avg_credential[3],
    '150 credenciales': tiempos_avg_credential[4],
    '200 credenciales': tiempos_avg_credential[5],
    '250 credenciales': tiempos_avg_credential[6],
    '300 credenciales': tiempos_avg_credential[7],
    '400 credenciales': tiempos_avg_credential[8],
    '500 credenciales': tiempos_avg_credential[9],
})

dataavgcred.to_excel(f"tablas_excel/CR/sin_revocar/avgcred.xlsx")
dataavgcred.plot(kind='box', title=f"Avg per credential CR no revocation", legend=True, xlabel="Numero de credenciales", ylabel = "Tiempo (s)")
plt.show()

dataavgproof = pd.DataFrame({
    '10 credenciales' : tiempos_avg_proof[0],
    '20 credenciales' : tiempos_avg_proof[1],
    '50 credenciales' : tiempos_avg_proof[2],
    '100 credenciales': tiempos_avg_proof[3],
    '150 credenciales': tiempos_avg_proof[4],
    '200 credenciales': tiempos_avg_proof[5],
    '250 credenciales': tiempos_avg_proof[6],
    '300 credenciales': tiempos_avg_proof[7],
    '400 credenciales': tiempos_avg_proof[8],
    '500 credenciales': tiempos_avg_proof[9],
})

dataavgproof.to_excel(f"tablas_excel/CR/sin_revocar/avgproof.xlsx")
dataavgproof.plot(kind='box', title=f"Avg per proof CR no revocation", legend=True, xlabel="Numero de credenciales", ylabel = "Tiempo (s)")
plt.show()

datatotal = pd.DataFrame({
    '10 credenciales' : tiempos_total[0],
    '20 credenciales' : tiempos_total[1],
    '50 credenciales' : tiempos_total[2],
    '100 credenciales': tiempos_total[3],
    '150 credenciales': tiempos_total[4],
    '200 credenciales': tiempos_total[5],
    '250 credenciales': tiempos_total[6],
    '300 credenciales': tiempos_total[7],
    '400 credenciales': tiempos_total[8],
    '500 credenciales': tiempos_total[9],
})

datatotal.to_excel(f"tablas_excel/CR/sin_revocar/total.xlsx")
datatotal.plot(kind='box', title=f"Total CR no revocation", legend=True, xlabel="Numero de credenciales", ylabel = "Tiempo (s)")
plt.show()

#Se pasa las credenciales a string para el dataframe
credenciales_string = []
for credentials in credenciales:
    credenciales_string.append(str(credentials))

#Vectores con las medias de las pruebas para cada credencial
medias_startup = []
medias_connect = []
medias_publish = []
medias_avg_credential = []
medias_avg_proof = []
medias_total = []

#Creacion de directorios para tablas excel
if(not os.path.exists(f"/home/rafa/aca-py-performance/demo/tablas_excel/CR/sin_revocar")):
    os.makedirs(f"/home/rafa/aca-py-performance/demo/tablas_excel/sin_revocar")
        
for cred in range(1, len(credenciales)+1):

    #Se crea un dataFrame para cada credencial
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

    #Se pasa a float y se muestran los datos estadísticos de las pruebas para cada credencial
    dataframe = dataframe.astype(float)
    print(f"Datos estadísticos para {credenciales[cred-1]} credenciales \n")
    print(dataframe.describe())
    print("\n")
    
    dataframe.to_excel(f"tablas_excel/CR/sin_revocar/{credenciales[cred-1]}_credenciales.xlsx")
    dataframe.describe().to_excel(f"tablas_excel/CR/sin_revocar/{credenciales[cred-1]}_credenciales_describe.xlsx")

    #Se plotea un esquema de cajas y bigotes del dataFrame creado
    dataframe.plot(kind='box', title=f"Pruebas para {credenciales[cred-1]} credenciales")

    #Se añade al vector de medias la media de cada tiempo del dataFrame
    medias_startup.append(dataframe["Startup"].mean())
    medias_connect.append(dataframe["Connect"].mean())
    medias_publish.append(dataframe["Publish"].mean())
    medias_avg_credential.append(dataframe["Average cred"].mean())
    medias_avg_proof.append(dataframe["Average proof"].mean())
    medias_total.append(dataframe["Total"].mean())

#Para mostrar los ploteos del bucle for
plt.show()

#Se crea un dataFrame con las medias calculadas anteriormente 
df_final = pd.DataFrame({
        'Startup': medias_startup,
        'Connect': medias_connect,
        'Publish': medias_publish,
        'Average cred': medias_avg_credential,
        'Average proof': medias_avg_proof,
        'Total': medias_total,
}, index = credenciales_string)

#Se muestran los datos de la tabla final con los tiempos para cada numero de credencial
print(f"TABLA FINAL \n")
print(df_final)
df_final.to_excel("tablas_excel/CR/sin_revocar/tablafinal.xlsx")

#Se plotea una grafica para cada tipo de tiempo con las medias calculadas para cada numero de credencial
df_final["Startup"].plot(title="FINAL Startup")
plt.show()

df_final["Connect"].plot(title="FINAL Connect")
plt.show()

df_final["Publish"].plot(title="FINAL Publish")
plt.show()

df_final["Average cred"].plot(title="FINAL Average cred")
plt.show()

df_final["Average proof"].plot(title="FINAL Average proof")
plt.show()

df_final["Total"].plot(title="FINAL Total")
plt.show()