'proof_presentation_CS: script que ejecuta el entorno de credenciales simples (sin opción a revocación). El resultado se almacena en ficheros logs.'

import os
import subprocess

credenciales = [10, 20, 50, 100, 150, 200, 250, 300, 400, 500]
pruebas = 25

pid = os.getpid()

for cred in credenciales:
    for prueba in range(1, pruebas + 1):

        if(not os.path.exists(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/sin_revocar/{cred}_credenciales")):
            os.makedirs(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/sin_revocar/{cred}_credenciales")
            os.makedirs(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/sin_revocar/{cred}_credenciales/datosCPUyRAM")
        cpu_process = subprocess.Popen(["bash", "cpu_y_ram.sh", f"{pid}", f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/sin_revocar/{cred}_credenciales/datosCPUyRAM/CPU_{cred}_credenciales_prueba_{prueba}.txt"])
        p = subprocess.Popen(["bash", "run_demo", "performance", "--count", f"{cred}", "--proof_presentation", "--revocation"], stdout=subprocess.PIPE, text= True)
        file = open(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/sin_revocar/{cred}_credenciales/prueba{prueba}_con_{cred}_credenciales.txt","w")
        file.write(p.communicate()[0])
        file.close()

        #matar proceso cpu y ram
        cpu_process.kill()

print("Ejecución finalizada")