
'''
AUTOR: RAFAEL ADAN LOPEZ.
FECHA: 20 DE JUNIO DE 2022

UNIVERSIDAD DE GRANADA
TRABAJO DE FIN DE GRADO: EVALUACION DE RENDIMIENTO DE ENTORNO SSI BASADO EN BLOCKCHAIN


SCRIPT PARA EJECUTAR UN ENTORNO DE PRUEBAS DE EMISION Y POSTERIOR PRESENTACION DE CREDENCIALES SIMPLES (CS) (SIN POSIBILIDAD DE REVOCACION) ENTRE DOS AGENTES. 

CAMBIAR LOS DIRECTORIOS PARA USO DEL SCRIPT, PUESTO QUE ESTA PUESTO LA RUTA DEL DESARROLLADOR.

'''

#Importacion de librerias necesarias
import subprocess
import os

#Numero de credenciales que se quieran probar
credenciales = [10, 20, 50, 100, 150, 200, 250, 300, 400, 500]

#Numero de pruebas realizadas con cada credencial
pruebas = 25

pid = os.getpid()


for cred in credenciales:
    for prueba in range(1, pruebas + 1):
        
        #En caso de no existir el directorio para guardar los logs, lo crea
        if(not os.path.exists(f"/home/rafa/aca-py-performance/demo/pruebas/CS/{cred}_credenciales")):
            os.makedirs(f"/home/rafa/aca-py-performance/demo/pruebas/CS/{cred}_credenciales")
            os.makedirs(f"/home/rafa/aca-py-performance/demo/pruebas/CS/{cred}_credenciales/datosCPUyRAM")
        
        #Ejecuta dos procesos: la prueba en sí utilizando el script bash run_demo y un proceso que mide la CPU y RAM utilizada y lo guarda en logs
        cpu_process = subprocess.Popen(["bash", "cpu_y_ram.sh", f"{pid}", f"/home/rafa/aca-py-performance/demo/pruebas/CS/{cred}_credenciales/datosCPUyRAM/CPU_{cred}_credenciales_prueba_{prueba}.txt"])
        p = subprocess.Popen(["bash", "run_demo", "performance", "--count", f"{cred}", "--proof_presentation"], stdout=subprocess.PIPE, text= True)

        #Se guarda la salida del proceso en ficheros logs
        file = open(f"/home/rafa/aca-py-performance/demo/pruebas/CS/{cred}_credenciales/prueba{prueba}_con_{cred}_credenciales.txt","w")
        file.write(p.communicate()[0])
        file.close()

        #Matar proceso de CPU y RAM
        cpu_process.kill()

        #Optimizacion de las imagenes docker para que no consuman espacio adicional
        subprocess.Popen('yes | docker image prune', shell = 'False')
        

print("Ejecucion finalizada")
