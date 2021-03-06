
'''
AUTOR: RAFAEL ADAN LOPEZ.
FECHA: 20 DE JUNIO DE 2022

UNIVERSIDAD DE GRANADA
TRABAJO DE FIN DE GRADO: EVALUACION DE RENDIMIENTO DE ENTORNO SSI BASADO EN BLOCKCHAIN


SCRIPT PARA EJECUTAR UN ENTORNO DE PRUEBAS DE EMISION Y POSTERIOR PRESENTACION DE CREDENCIALES REVOCABLES (CR) 
(CON POSIBILIDAD DE REVOCACION) ENTRE DOS AGENTES, Y REVOCANDO DE UNA EN UNA.

CAMBIAR LOS DIRECTORIOS PARA USO DEL SCRIPT, PUESTO QUE ESTA PUESTO LA RUTA DEL DESARROLLADOR.

'''

#Importación de las librerías necesarias
import os
import subprocess

def main(
    tails_server_base_url: str = None, #url del servidor tails para las revocaciones
):
  
    #Número de credenciales que se quieren probar y el número de pruebas a realizar con cada una
    credenciales = [10, 20, 50, 100, 150, 200, 250, 300, 400, 500]
    pruebas = 25

    pid = os.getpid()

    for cred in credenciales:
        for prueba in range(14, pruebas + 1):
            
            #En caso de no existir el directorio para guardar los logs, lo crea.
            if(not os.path.exists(f"/home/rafa/aca-py-performance/demo/pruebas/CR/revocando_uno_a_uno/{cred}_credenciales")):
                os.makedirs(f"/home/rafa/aca-py-performance/demo/pruebas/CR/revocando_uno_a_uno/{cred}_credenciales")
                os.makedirs(f"/home/rafa/aca-py-performance/demo/pruebas/CR/revocando_uno_a_uno/{cred}_credenciales/datosCPUyRAM")

            #Ejecuta dos procesos: la prueba en sí utilizando el script bash run_demo y un proceso que mide la CPU y RAM utilizada y lo guarda en logs
            cpu_process = subprocess.Popen(["bash", "cpu_y_ram.sh", f"{pid}", f"/home/rafa/aca-py-performance/demo/pruebas/CR/revocando_uno_a_uno/{cred}_credenciales/datosCPUyRAM/CPU_{cred}_credenciales_prueba_{prueba}.txt"])
            p = subprocess.Popen(["bash", "run_demo", "performance", "--count", f"{cred}", "--revocation", "--revoke_credentials", "--tails-server-base-url", f"{tails_server_base_url}"], stdout=subprocess.PIPE, text= True)
            
            #Se guarda la salida del proceso en ficheros logs
            file = open(f"/home/rafa/aca-py-performance/demo/pruebas/CR/revocando_uno_a_uno/{cred}_credenciales/prueba{prueba}_con_{cred}_credenciales.txt","w")
            file.write(p.communicate()[0])
            file.close()

            #Matar proceso cpu y ram
            cpu_process.kill()

            #Optimización de las imágenes docker para que no consuman espacio adicional
            subprocess.Popen('yes | docker image prune', shell = 'False')

    print("Ejecución finalizada")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Script para ejecución entorno CR sin llegar a revocar"
    )

    parser.add_argument(
        "--tails-server-base-url",
        type=str,
        metavar="<tails-server-base-url>",
        help="Tails server base url",
    )
    args = parser.parse_args()

    try:
            main(
                args.tails_server_base_url
            )
        
    except KeyboardInterrupt:
        os._exit(1)

