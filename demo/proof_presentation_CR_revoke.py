import os
import subprocess
import asyncio

async def main(
   tails_server_base_url: str = None, #url del servidor tails para las revocaciones
):
    credenciales = [10, 20, 50, 100, 150, 200, 250, 300, 400, 500]
    pruebas = 25

    pid = os.getpid()

    for cred in credenciales:
        for prueba in range(1, pruebas + 1):

            if(not os.path.exists(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/revocando/{cred}_credenciales")):
                os.makedirs(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/revocando/{cred}_credenciales")
                os.makedirs(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/revocando/{cred}_credenciales/datosCPUyRAM")
            cpu_process = subprocess.Popen(["bash", "cpu_y_ram.sh", f"{pid}", f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/revocando/{cred}_credenciales/datosCPUyRAM/CPU_{cred}_credenciales_prueba_{prueba}.txt"])
            p = subprocess.Popen(["bash", "run_demo", "performance", "--count", f"{cred}", "--proof_presentation", "--revocation", "--revoke_credentials", "--publish_revocations_at_once", "--tails-server-base-url", f"{tails_server_base_url}" ], stdout=subprocess.PIPE, text= True)
            file = open(f"/home/rafa/aries-cloudagent-python/demo/pruebas/CR/revocando/{cred}_credenciales/prueba{prueba}_con_{cred}_credenciales.txt","w")
            file.write(p.communicate()[0])
            file.close()

            #matar proceso cpu y ram
            cpu_process.kill()

    print("Ejecución finalizada")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Script para ejecución entorno CR y publicando la revocación de una vez"
    )
    
    parser.add_argument(
        "--tails-server-base-url",
        type=str,
        metavar="<tails-server-base-url>",
        help="Tails server base url",
 


    try:
        asyncio.get_event_loop().run_until_complete(
            main(
                args.tails_server_base_url,
            )
        )
    except KeyboardInterrupt:
        os._exit(1)
