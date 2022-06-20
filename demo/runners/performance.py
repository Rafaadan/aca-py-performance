import asyncio
import datetime
import logging
import os
import random
import sys
import time
import json
from typing import Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runners.support.agent import (  # noqa:E402
    DemoAgent,
    default_genesis_txns,
    start_mediator_agent,
    connect_wallet_to_mediator,
)
from runners.agent_container import SELF_ATTESTED
from runners.support.utils import (  # noqa:E402
    check_requires, #comprobar requerimientos de indy y librerias
    log_msg, #printear mensaje en la terminal
    log_timer, #contador
    log_status,
    progress, #para la barra de progreso
)

from runners.support.agent import (  # noqa:E402
    CRED_FORMAT_INDY,
    CRED_FORMAT_JSON_LD,
    SIG_TYPE_BLS,
)

CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview" 
LOGGER = logging.getLogger(__name__)
TAILS_FILE_COUNT = int(os.getenv("TAILS_FILE_COUNT", 100))

#clase general para los agentes

class BaseAgent(DemoAgent):
    def __init__(
        self,
        ident: str, #nombre
        port: int, #puerto
        prefix: str = None,
        **kwargs,
    ):
        if prefix is None:
            prefix = ident
        super().__init__(ident, port, port + 1, prefix=prefix, **kwargs)
        self._connection_id = None
        self._connection_ready = None
        self.credential_state = {}
        self.credential_event = asyncio.Event()
        self.proof_state = {}
        self.proof_event = asyncio.Event()
        self.revocations = []
        self.ping_state = {} 
        self.ping_event = asyncio.Event()
        self.sent_pings = set()

    #funcion que devuelve el conection id
    @property
    def connection_id(self) -> str:
        return self._connection_id

    #funcion que le da un valor al connection id
    @connection_id.setter
    def connection_id(self, conn_id: str):
        self._connection_id = conn_id
        self._connection_ready = asyncio.Future() #crea un objeto Future

    async def detect_connection(self):
        if not self._connection_ready:
            raise Exception("No connection to await")
        await self._connection_ready #La corrutina se parará (o cederá el control mejor dicho) hasta que el objeto termine (el future)
        self._connection_ready = None


    #TODOS LOS HANDLES SE LLAMAN CADA VEZ QUE EL AGENTE/FRAMEWORK MANDA UN WEBHOOK
    async def handle_oob_invitation(self, message):
        pass

    #Nos devuelve el id de la conexión que hemos establecido y pone a true el objeto Futuro connection_ready
    async def handle_connections(self, payload):
        conn_id = payload["connection_id"]
        if (not self.connection_id) and (payload["state"] in ("invitation", "request")):
            self.connection_id = conn_id
        if conn_id == self.connection_id:
            if payload["state"] == "active" and not self._connection_ready.done():
                self.log("Connected")
                self._connection_ready.set_result(True)
    
    #Lo utiliza el agente (API) para notificar de la revocación (Alice en este caso)
    async def handle_revocation_notification(self, payload):
        print(payload)

    #Devuelve el id de la credencial que hemos emitido, lo guarda en credential_state junto con su estado
    async def handle_issue_credential(self, payload):
        cred_ex_id = payload["credential_exchange_id"]
        self.credential_state[cred_ex_id] = payload["state"]
        self.credential_event.set()

    async def handle_issue_credential_v2_0(self, payload):
        cred_ex_id = payload["cred_ex_id"]
        self.credential_state[cred_ex_id] = payload["state"]
        self.credential_event.set()

    async def handle_present_proof_v2_0(self, message): 
        state = message.get("state")
        pres_ex_id = message["pres_ex_id"]
        self.proof_state[pres_ex_id] = state
        self.proof_event.set()
        self.log(f"Presentation: state = {state}, pres_ex_id = {pres_ex_id}")

        if state == "request-received":
            # prover role
            log_status(
                "#24 Query for credentials in the wallet that satisfy the proof request"
            )
            pres_request_indy = message["by_format"].get("pres_request", {}).get("indy")
            pres_request_dif = message["by_format"].get("pres_request", {}).get("dif")

            if pres_request_indy:
                # include self-attested attributes (not included in credentials)
                creds_by_reft = {}
                revealed = {}
                self_attested = {}
                predicates = {}

                try:
                    # select credentials to provide for the proof
                    creds = await self.admin_GET(
                        f"/present-proof-2.0/records/{pres_ex_id}/credentials"
                    )
                    if creds:
                        if "timestamp" in creds[0]["cred_info"]["attrs"]:
                            sorted_creds = sorted(
                                creds,
                                key=lambda c: int(c["cred_info"]["attrs"]["timestamp"]),
                                reverse=True,
                            )
                        else:
                            sorted_creds = creds
                        for row in sorted_creds:
                            for referent in row["presentation_referents"]:
                                if referent not in creds_by_reft:
                                    creds_by_reft[referent] = row

                    for referent in pres_request_indy["requested_attributes"]:
                        if referent in creds_by_reft:
                            revealed[referent] = {
                                "cred_id": creds_by_reft[referent]["cred_info"][
                                    "referent"
                                ],
                                "revealed": True,
                            }
                        else:
                            self_attested[referent] = "my self-attested value"

                    for referent in pres_request_indy["requested_predicates"]:
                        if referent in creds_by_reft:
                            predicates[referent] = {
                                "cred_id": creds_by_reft[referent]["cred_info"][
                                    "referent"
                                ]
                            }

                    log_status("#25 Generate the proof")
                    request = {
                        "indy": {
                            "requested_predicates": predicates,
                            "requested_attributes": revealed,
                            "self_attested_attributes": self_attested,
                        }
                    }
                except ClientError:
                    pass

            elif pres_request_dif:
                try:
                    # select credentials to provide for the proof
                    creds = await self.admin_GET(
                        f"/present-proof-2.0/records/{pres_ex_id}/credentials"
                    )
                    if creds and 0 < len(creds):
                        creds = sorted(
                            creds,
                            key=lambda c: c["issuanceDate"],
                            reverse=True,
                        )
                        record_id = creds[0]["record_id"]
                    else:
                        record_id = None

                    log_status("#25 Generate the proof")
                    request = {
                        "dif": {},
                    }
                    # specify the record id for each input_descriptor id:
                    request["dif"]["record_ids"] = {}
                    for input_descriptor in pres_request_dif["presentation_definition"][
                        "input_descriptors"
                    ]:
                        request["dif"]["record_ids"][input_descriptor["id"]] = [
                            record_id,
                        ]
                    log_msg("presenting ld-presentation:", request)

                    # NOTE that the holder/prover can also/or specify constraints by including the whole proof request
                    # and constraining the presented credentials by adding filters, for example:
                    #
                    # request = {
                    #     "dif": pres_request_dif,
                    # }
                    # request["dif"]["presentation_definition"]["input_descriptors"]["constraints"]["fields"].append(
                    #      {
                    #          "path": [
                    #              "$.id"
                    #          ],
                    #          "purpose": "Specify the id of the credential to present",
                    #          "filter": {
                    #              "const": "https://credential.example.com/residents/1234567890"
                    #          }
                    #      }
                    # )
                    #
                    # (NOTE the above assumes the credential contains an "id", which is an optional field)

                except ClientError:
                    pass

            else:
                raise Exception("Invalid presentation request received")

            log_status("#26 Send the proof to X: " + json.dumps(request))
            await self.admin_POST(
                f"/present-proof-2.0/records/{pres_ex_id}/send-presentation",
                request,
            )

        elif state == "presentation-received":
            # verifier role
            log_status("#27 Process the proof provided by X")
            log_status("#28 Check if proof is valid")
            proof = await self.admin_POST(
                f"/present-proof-2.0/records/{pres_ex_id}/verify-presentation"
            )
            self.log("Proof =", proof["verified"])
            self.last_proof_received = proof

        elif state == "abandoned":
            log_status("Presentation exchange abandoned")
            self.log("Problem report message:", message.get("error_msg"))
    
    async def handle_issue_credential_v2_0_indy(self, payload):
        rev_reg_id = payload.get("rev_reg_id")
        cred_rev_id = payload.get("cred_rev_id")
        if rev_reg_id and cred_rev_id:
            self.revocations.append((rev_reg_id, cred_rev_id))

    async def handle_issuer_cred_rev(self, message):
        pass

    async def handle_ping(self, payload):
        
        thread_id = payload["thread_id"]
        if thread_id in self.sent_pings or (
            payload["state"] == "received"
            and payload["comment"]
            and payload["comment"].startswith("test-ping")
        ):
            self.ping_state[thread_id] = payload["state"]
            self.ping_event.set()

    async def check_received_creds(self) -> Tuple[int, int]:
        while True:
            self.credential_event.clear() #Limpia el evento a false
            pending = 0
            total = len(self.credential_state) #numero de credenciales listas
            for result in self.credential_state.values():
                if result != "done" and result != "credential_acked":
                    pending += 1 #va sumando las credenciales no recibidas  
            if self.credential_event.is_set():
                continue
            return pending, total
    async def check_received_proofs(self) -> Tuple[int, int]:
        while True:
            self.proof_event.clear() #Limpia el evento a false
            pending = 0
            total = len(self.proof_state) #numero de credenciales listas
            for result in self.proof_state.values():
                if result != "done" and result != "credential_acked":
                    pending += 1 #va sumando las credenciales no recibidas  
            if self.proof_event.is_set():
                continue
            return pending, total

    #Bloquea la corrutina hasta que haya un evento de credencial (es decir se ponga a true)
    async def update_creds(self):
        await self.credential_event.wait()

    async def update_proofs(self):
        await self.proof_event.wait()

    async def check_received_pings(self) -> Tuple[int, int]:
        while True:
            self.ping_event.clear() #Limpia el evento a false
            result = {}
            for thread_id, state in self.ping_state.items():
                if not result.get(state):
                    result[state] = set()
                result[state].add(thread_id)
            if self.ping_event.is_set():
                continue
            return result

    #Bloquea la corrutina hasta que haya un evento de ping (es decir se ponga a true)
    async def update_pings(self):
        await self.ping_event.wait()

    #Llama a la API para mandar un ping
    async def send_ping(self, ident: str = None) -> str:
        resp = await self.admin_POST(
            f"/connections/{self.connection_id}/send-ping",
            {"comment": f"test-ping {ident}"},
        )
        self.sent_pings.add(resp["thread_id"])

    #devuelve una exepción (o ninguna) si la tarea ha terminado
    def check_task_exception(self, fut: asyncio.Task):
        if fut.done():
            try:
                exc = fut.exception()
            except asyncio.CancelledError as e:
                exc = e
            if exc:
                self.log(f"Task raised exception: {str(exc)}")

#Clase de Alice
class AliceAgent(BaseAgent):
    def __init__(self, port: int, **kwargs):
        super().__init__("Alice", port, seed=None, **kwargs)
        self.extra_args = [
            "--auto-accept-invites",
            "--auto-accept-requests",
            "--auto-respond-credential-offer",
            "--auto-store-credential",
            "--monitor-ping",
        ]
        self.timing_log = "logs/alice_perf.log"

    #Le pide a la API que le devuelva la definición de credencial (la cual le pide al ledger)
    async def fetch_credential_definition(self, cred_def_id):
        return await self.admin_GET(f"/credential-definitions/{cred_def_id}")

    #Le manda a la API una proposición de credencial para mandarsela al emisor
    async def propose_credential(
        self,
        cred_attrs: dict,
        cred_def_id: str,
        comment: str = None,
        auto_remove: bool = True,
    ):
        cred_preview = {
            "attributes": [{"name": n, "value": v} for (n, v) in cred_attrs.items()]
        }
        await self.admin_POST(
            "/issue-credential/send-proposal",
            {
                "connection_id": self.connection_id,
                "cred_def_id": cred_def_id,
                "credential_proposal": cred_preview,
                "comment": comment,
                "auto_remove": auto_remove,
            },
        )

#Clase de Faber
class FaberAgent(BaseAgent):
    def __init__(self, port: int, **kwargs):
        super().__init__("Faber", port, seed="random", **kwargs)
        self.extra_args = [
            "--auto-accept-invites",
            "--auto-accept-requests",
            "--monitor-ping",
            "--auto-respond-credential-proposal",
            "--auto-respond-credential-request",
        ]
        self.schema_id = None
        self.credential_definition_id = None
        self.revocation_registry_id = None
        self.cred_type = CRED_FORMAT_INDY

    #Le manda a la API una definición de credencial (y el esquema) para que la publique en el ledger
    async def publish_defs(self, support_revocation: bool = False):
        # create a schema
        self.log("Publishing test schema")
        version = format(
            "%d.%d.%d"
            % (random.randint(1, 101), random.randint(1, 101), random.randint(1, 101))
        )
        schema_body = {
            "schema_name": "degree schema",
            "schema_version": version,
            "attributes": ["name", "date", "degree", "birthdate_dateint","age"],
        }
        schema_response = await self.admin_POST("/schemas", schema_body)
        self.schema_id = schema_response["schema_id"]
        self.log(f"Schema ID: {self.schema_id}")

        # create a cred def for the schema
        self.log("Publishing test credential definition")
        credential_definition_body = {
            "schema_id": self.schema_id,
            "support_revocation": support_revocation,
            "revocation_registry_size": TAILS_FILE_COUNT,
        }
        credential_definition_response = await self.admin_POST(
            "/credential-definitions", credential_definition_body
        )
        self.credential_definition_id = credential_definition_response[
            "credential_definition_id"
        ]
        self.log(f"Credential Definition ID: {self.credential_definition_id}")

    #Le manda a la API una credencial para enviarsela al titular
    async def send_credential(
        self, cred_attrs: dict, comment: str = None, auto_remove: bool = True
    ):
        cred_preview = {
            "@type": CRED_PREVIEW_TYPE,
            "attributes": [{"name": n, "value": v} for (n, v) in cred_attrs.items()],
        }
        await self.admin_POST(
            "/issue-credential-2.0/send",
            {
                "filter": {"indy": {"cred_def_id": self.credential_definition_id}},
                "auto_remove": auto_remove,
                "comment": comment,
                "connection_id": self.connection_id,
                "credential_preview": cred_preview,
            },
        )

    #Le manda a la API una credencial que revocar. pasa como argumento el id de la credencial
    async def revoke_credential(self, rev_reg_id, cred_rev_id, publish, connection_id):
        rev = {
            "rev_reg_id": rev_reg_id,
            "cred_rev_id": cred_rev_id,
            "publish": publish,
            "connection_id": connection_id,
            "notify": False,
            # leave out thread_id, let aca-py generate
            # "thread_id": "12345678-4444-4444-4444-123456789012",
            "comment": "Revocation reason goes here ...",
            }
        await self.admin_POST(
            "/revocation/revoke", rev
        )
        
    '''async def revoke_credential_without_publishing(self, rev: dict):
        await self.admin_POST(
            "/revocation/revoke", rev
        )'''
    async def publish_revocations(self):
        await self.admin_POST(
            "/revocation/publish-revocations",{}
        )

    async def generate_proof_request_web_request(
            self, aip, cred_type, revocation, exchange_tracing, connectionless=False
    ):
        age = 18
        d = datetime.date.today()
        birth_date = datetime.date(d.year - age, d.month, d.day)
        birth_date_format = "%Y%m%d"
        if aip == 10:
            req_attrs = [
                {
                    "name": "name",
                    "restrictions": [{"schema_name": "degree schema"}],
                },
                {
                    "name": "date",
                    "restrictions": [{"schema_name": "degree schema"}],
                },
            ]
            if revocation:
                req_attrs.append(
                    {
                        "name": "degree",
                        "restrictions": [{"schema_name": "degree schema"}],
                        "non_revoked": {"to": int(time.time() - 1)},
                    },
                )
            else:
                req_attrs.append(
                    {
                        "name": "degree",
                        "restrictions": [{"schema_name": "degree schema"}],
                    }
                )
            if SELF_ATTESTED:
                # test self-attested claims
                req_attrs.append(
                    {"name": "self_attested_thing"},
                )
            req_preds = [
                # test zero-knowledge proofs
                {
                    "name": "birthdate_dateint",
                    "p_type": "<=",
                    "p_value": int(birth_date.strftime(birth_date_format)),
                    "restrictions": [{"schema_name": "degree schema"}],
                }
            ]
            indy_proof_request = {
                "name": "Proof of Education",
                "version": "1.0",
                "requested_attributes": {
                    f"0_{req_attr['name']}_uuid": req_attr for req_attr in req_attrs
                },
                "requested_predicates": {
                    f"0_{req_pred['name']}_GE_uuid": req_pred for req_pred in req_preds
                },
            }

            if revocation:
                indy_proof_request["non_revoked"] = {"to": int(time.time())}

            proof_request_web_request = {
                "proof_request": indy_proof_request,
                "trace": exchange_tracing,
            }
            if not connectionless:
                proof_request_web_request["connection_id"] = self.connection_id
            return proof_request_web_request

        elif aip == 20:
            if cred_type == CRED_FORMAT_INDY:
                req_attrs = [
                    {
                        "name": "name",
                        "restrictions": [{"schema_name": "degree schema"}],
                    },
                    {
                        "name": "date",
                        "restrictions": [{"schema_name": "degree schema"}],
                    },
                ]
                if revocation:
                    req_attrs.append(
                        {
                            "name": "degree",
                            "restrictions": [{"schema_name": "degree schema"}],
                            "non_revoked": {"to": int(time.time() - 1)},
                        },
                    )
                else:
                    req_attrs.append(
                        {
                            "name": "degree",
                            "restrictions": [{"schema_name": "degree schema"}],
                        }
                    )
                if SELF_ATTESTED:
                    # test self-attested claims
                    req_attrs.append(
                        {"name": "self_attested_thing"},
                    )
                req_preds = [
                    # test zero-knowledge proofs
                    {
                        "name": "birthdate_dateint",
                        "p_type": "<=",
                        "p_value": int(birth_date.strftime(birth_date_format)),
                        "restrictions": [{"schema_name": "degree schema"}],
                    }
                ]
                indy_proof_request = {
                    "name": "Proof of Education",
                    "version": "1.0",
                    "requested_attributes": {
                        f"0_{req_attr['name']}_uuid": req_attr for req_attr in req_attrs
                    },
                    "requested_predicates": {
                        f"0_{req_pred['name']}_GE_uuid": req_pred
                        for req_pred in req_preds
                    },
                }

                if revocation:
                    indy_proof_request["non_revoked"] = {"to": int(time.time())}

                proof_request_web_request = {
                    "presentation_request": {"indy": indy_proof_request},
                    "trace": exchange_tracing,
                }
                if not connectionless:
                    proof_request_web_request["connection_id"] = self.connection_id
                return proof_request_web_request

            elif cred_type == CRED_FORMAT_JSON_LD:
                proof_request_web_request = {
                    "comment": "test proof request for json-ld",
                    "presentation_request": {
                        "dif": {
                            "options": {
                                "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                                "domain": "4jt78h47fh47",
                            },
                            "presentation_definition": {
                                "id": "32f54163-7166-48f1-93d8-ff217bdb0654",
                                "format": {"ldp_vp": {"proof_type": [SIG_TYPE_BLS]}},
                                "input_descriptors": [
                                    {
                                        "id": "citizenship_input_1",
                                        "name": "EU Driver's License",
                                        "schema": [
                                            {
                                                "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
                                            },
                                            {
                                                "uri": "https://w3id.org/citizenship#PermanentResident"
                                            },
                                        ],
                                        "constraints": {
                                            "limit_disclosure": "required",
                                            "is_holder": [
                                                {
                                                    "directive": "required",
                                                    "field_id": [
                                                        "1f44d55f-f161-4938-a659-f8026467f126"
                                                    ],
                                                }
                                            ],
                                            "fields": [
                                                {
                                                    "id": "1f44d55f-f161-4938-a659-f8026467f126",
                                                    "path": [
                                                        "$.credentialSubject.familyName"
                                                    ],
                                                    "purpose": "The claim must be from one of the specified person",
                                                    "filter": {"const": "SMITH"},
                                                },
                                                {
                                                    "path": [
                                                        "$.credentialSubject.givenName"
                                                    ],
                                                    "purpose": "The claim must be from one of the specified person",
                                                },
                                            ],
                                        },
                                    }
                                ],
                            },
                        }
                    },
                }
                if not connectionless:
                    proof_request_web_request["connection_id"] = self.connection_id
                return proof_request_web_request

            else:
                raise Exception(f"Error invalid credential type: {self.cred_type}")

        else:
            raise Exception(f"Error invalid AIP level: {self.aip}")

    async def send_proof_request(self, exchange_tracing: bool = False):
        log_msg("#20 Request proof of degree from alice")
        if self.aip == 10:
            proof_request_web_request = (
                await self.generate_proof_request_web_request(
                    self.aip,
                    self.cred_type,
                    self.revocation,
                    exchange_tracing,
                            )
                )
            await self.admin_POST(
                            "/present-proof/send-request", proof_request_web_request
                )
            pass

        elif self.aip == 20:
            if self.cred_type == CRED_FORMAT_INDY:
                            proof_request_web_request = (
                                await self.generate_proof_request_web_request(
                                    self.aip,
                                    self.cred_type,
                                    self.revocation,
                                    exchange_tracing,
                                )
                            )

            elif self.cred_type == CRED_FORMAT_JSON_LD:
                            proof_request_web_request = (
                                await self.generate_proof_request_web_request(
                                    self.aip,
                                    self.cred_type,
                                    self.revocation,
                                    exchange_tracing,
                                )
                            )

            else:
                raise Exception(
                                "Error invalid credential type:" + self.cred_type
                            )

            await self.admin_POST(
                            "/present-proof-2.0/send-request", proof_request_web_request
                        )

        else:
                        raise Exception(f"Error invalid AIP level: {self.aip}")

async def main(
    start_port: int,
    threads: int = 20, #Numero de hebras
    action: str = None, #accion que puede ser ping o credenciales
    show_timing: bool = False,
    multitenant: bool = False,  #activa multitenancia
    mediation: bool = False,    #activa mediación
    multi_ledger: bool = False, #activa multi-ledger
    use_did_exchange: bool = False, #activa did-exchange
    revocation: bool = False,   #activa revocación (pero no implica que se rec)
    tails_server_base_url: str = None, #url del servidor tails para las revocaciones
    issue_count: int = 300, #numero de credenciales/pings
    batch_size: int = 30,   #¿?Tamaño de las credenciales/pings
    wallet_type: str = None,
    arg_file: str = None,
    proof_presentation: bool = False, #activa presentación de credenciales
    revoke_credentials: bool = False, #revoca las credenciales emitidas
    publish_revocations_at_once: bool = False, #Publica todas las revocaciones en una sola transición
):
    
    
    #Configuración del ledger (o multi-ledger)
    if multi_ledger:
        genesis = None
        multi_ledger_config_path = "./demo/multi_ledger_config.yml"
    else:
        genesis = await default_genesis_txns()
        multi_ledger_config_path = None
        if not genesis:
            print("Error retrieving ledger genesis transactions")
            sys.exit(1)

    alice = None
    faber = None
    alice_mediator_agent = None
    faber_mediator_agent = None
    run_timer = log_timer("Total runtime:") #Contador para el tiempo total de ejecución
    run_timer.start()

    try:
        #instancia el agente alice
        alice = AliceAgent(
            start_port,
            genesis_data=genesis,
            genesis_txn_list=multi_ledger_config_path,
            timing=show_timing,
            multitenant=multitenant,
            mediation=mediation,
            wallet_type=wallet_type,
            arg_file=arg_file,
            revocation=revocation,
        )

        #abro los webhooks para escuchar notificaciones de la API/framework/agente
        await alice.listen_webhooks(start_port + 2)

        #instancio el agente faber
        faber = FaberAgent(
            start_port + 3,
            genesis_data=genesis,
            genesis_txn_list=multi_ledger_config_path,
            timing=show_timing,
            tails_server_base_url=tails_server_base_url,
            multitenant=multitenant,
            mediation=mediation,
            wallet_type=wallet_type,
            arg_file=arg_file,
            revocation=revocation
        )

        #abro los webhooks
        await faber.listen_webhooks(start_port + 5)

        #registro el did en el ledger (para alice no hace falta)
        await faber.register_did() 


        #inicialización de los agentes
        with log_timer("Startup duration:"): #contador
            await alice.start_process() #inicializo los agentes, con esto me refiero al framework. 
            await faber.start_process() #se puede ver mejor en la función, donde se llama a otro script independiente de python
            # y se tiene el agente como subproceso del controlador


            #en caso de activar mediación, crear los agentes mediadores
            if mediation:
                alice_mediator_agent = await start_mediator_agent(
                    start_port + 8, genesis, multi_ledger_config_path
                )
                if not alice_mediator_agent:
                    raise Exception("Mediator agent returns None :-(")
                faber_mediator_agent = await start_mediator_agent(
                    start_port + 11, genesis, multi_ledger_config_path
                )
                if not faber_mediator_agent:
                    raise Exception("Mediator agent returns None :-(")
            else:
                alice_mediator_agent = None
                faber_mediator_agent = None

        #conexión de alice y faber
        with log_timer("Connect duration:"):

            #se crea una cartera nueva en caso de tener activado multitenant
            if multitenant:
                # create an initial managed sub-wallet (also mediated)
                await alice.register_or_switch_wallet(
                    "Alice.initial",
                    webhook_port=None,
                    mediator_agent=alice_mediator_agent,
                )
                await faber.register_or_switch_wallet(
                    "Faber.initial",
                    public_did=True,
                    webhook_port=None,
                    mediator_agent=faber_mediator_agent,
                )
            #conexión de faber y alice a sus respectivos mediadores, si es el caso
            elif mediation:
                # we need to pre-connect the agent(s) to their mediator (use the same
                # mediator for both)
                if not await connect_wallet_to_mediator(alice, alice_mediator_agent):
                    log_msg("Mediation setup FAILED :-(")
                    raise Exception("Mediation setup FAILED :-(")
                if not await connect_wallet_to_mediator(faber, faber_mediator_agent):
                    log_msg("Mediation setup FAILED :-(")
                    raise Exception("Mediation setup FAILED :-(")


            invite = await faber.get_invite(use_did_exchange) #Genera la invitación
            await alice.receive_invite(invite["invitation"]) #Alice recibe la invitación
            await asyncio.wait_for(faber.detect_connection(), 30) #Esperamos a que faber detecte la conexión con un timeout de 30s

        #en caso de no ser pings (credenciales), se publica el esquema y la definicion de credencial
        if action != "ping":
            with log_timer("Publish duration:"):
                await faber.publish_defs(revocation)
            # cache the credential definition
            await alice.fetch_credential_definition(faber.credential_definition_id)

        if show_timing:
            await alice.reset_timing()
            await faber.reset_timing()
            if mediation:
                await alice_mediator_agent.reset_timing()
                await faber_mediator_agent.reset_timing()


        #Se crea un semáforo para limitir el uso de hebras. se podra adquirir una de las hebras y cuando se termine se libera
        semaphore = asyncio.Semaphore(threads)

        #devuelve el permiso porque se ha temrinado la proposición
        def done_propose(fut: asyncio.Task):
            semaphore.release()
            alice.check_task_exception(fut)

        #devuelve el permiso porque ya ha acabado el envío de credencial
        def done_send(fut: asyncio.Task):
            semaphore.release()
            faber.check_task_exception(fut)

        def done_proof(fut: asyncio.Task):
            semaphore.release()
            faber.check_task_exception(fut)

        #devuelve una credencial de prueba que varía la fecha según el índice
        def test_cred(index: int) -> dict:
            age = 24
            d = datetime.date.today()
            birth_date = datetime.date(d.year - age, d.month, d.day)
            birth_date_format = "%Y%m%d"
            return {
                "name": "Alice Smith",
                "date": f"{2020+index}-05-28",
                "degree": "Maths",
                "birthdate_dateint": birth_date.strftime(birth_date_format),
                "age": "24",
            }

        #función para proponer credenciales con el uso del semáforo
        async def propose_credential(index: int):
            await semaphore.acquire() #adquiere permiso del semaforo
            comment = f"propose test credential {index}"
            attributes = test_cred(index) #datos/atributos de la credencial de prueba
            asyncio.ensure_future(
                alice.propose_credential(
                    attributes, faber.credential_definition_id, comment, not revocation
                )
            ).add_done_callback(done_propose) #cuando se acabe el objeto Future, se llama a done_propose que libera el permiso del semáforo


        #función para mandar credencial con el uso del semáforo
        async def send_credential(index: int):
            await semaphore.acquire()
            comment = f"issue test credential {index}"
            attributes = test_cred(index) 
            asyncio.ensure_future(
                faber.send_credential(attributes, comment, not revocation)
            ).add_done_callback(done_send)

        #funcion para ir comprobando las credenciales emitidas/recibidas y que para cuando se hayan completado todas
        async def check_received_creds(agent, issue_count, pb):
            reported = 0
            iter_pb = iter(pb) if pb else None
            while True:
                pending, total = await agent.check_received_creds()
                complete = total - pending
                if reported == complete:
                    await asyncio.wait_for(agent.update_creds(), 30)
                    continue
                if iter_pb and complete > reported:
                    try:
                        while next(iter_pb) < complete:
                            pass
                    except StopIteration:
                        iter_pb = None
                reported = complete
                if reported == issue_count:
                    break

        #funcion para mandar ping usando semáforo
        async def send_ping(index: int):
            await semaphore.acquire()
            asyncio.ensure_future(faber.send_ping(str(index))).add_done_callback(
                done_send
            )

        #funcion para mandar una presentación de credencial usando semáforo
        async def send_proof(index: int):
            await semaphore.acquire()
            comment = f"proof test credential {index}"
            asyncio.ensure_future(
                faber.send_proof_request()
            ).add_done_callback(done_proof)

        async def check_received_proofs(agent, issue_count, pb):
            reported = 0
            iter_pb = iter(pb) if pb else None
            while True:
                pending, total = await agent.check_received_proofs()
                complete = total - pending
                if reported == complete:
                    await asyncio.wait_for(agent.update_proofs(), 30)
                    continue
                if iter_pb and complete > reported:
                    try:
                        while next(iter_pb) < complete:
                            pass
                    except StopIteration:
                        iter_pb = None
                reported = complete
                if reported == issue_count:
                    break

        async def check_received_pings(agent, issue_count, pb):
            reported = 0
            iter_pb = iter(pb) if pb else None
            while True:
                pings = await agent.check_received_pings()
                complete = sum(len(tids) for tids in pings.values())
                if complete == reported:
                    await asyncio.wait_for(agent.update_pings(), 30)
                    continue
                if iter_pb and complete > reported:
                    try:
                        while next(iter_pb) < complete:
                            pass
                    except StopIteration:
                        iter_pb = None
                reported = complete
                if reported >= issue_count:
                    break


        #Prepara los contadores                
        if action == "ping":
            recv_timer = faber.log_timer(f"Completed {issue_count} ping exchanges in")
            batch_timer = faber.log_timer(f"Started {batch_size} ping exchanges in")
        else:
            recv_timer = faber.log_timer(
                f"Completed {issue_count} credential exchanges in"
            )
            batch_timer = faber.log_timer(
                f"Started {batch_size} credential exchanges in"
            )

        #inicio de los contadores
        recv_timer.start()
        batch_timer.start()
        log_msg("Starting credential issues")
        #Se crea una barra de progreso
        with progress() as pb:
            receive_task = None
            try:

                #En primer lugar define la barra de la emisión, la barra de recepción, el tipo de accion y el tipo de funcion a usar (check_XXX)
                if action == "ping":
                    issue_pg = pb(range(issue_count), label="Sending pings") #barra emision 
                    receive_pg = pb(range(issue_count), label="Responding pings") #barra recepcion
                    check_received = check_received_pings
                    send = send_ping
                    completed = f"Done sending {issue_count} pings in" #texto a mostrar por el timer
                else:
                    issue_pg = pb(range(issue_count), label="Issuing credentials")
                    receive_pg = pb(range(issue_count), label="Receiving credentials")
                    check_received = check_received_creds
                    if action == "propose":
                        send = propose_credential
                    else:
                        send = send_credential
                    completed = f"Done starting {issue_count} credential exchanges in"

                issue_task = asyncio.ensure_future(
                    check_received(faber, issue_count, issue_pg)
                ) # Creamos la tarea con objeto futuro para faber
                issue_task.add_done_callback(faber.check_task_exception) #cuando acabe la tarea que llame a check_task_exception()
                receive_task = asyncio.ensure_future(
                    check_received(alice, issue_count, receive_pg)
                ) #hacemos lo mismo con alice
                receive_task.add_done_callback(alice.check_task_exception)

                #Las tres tareas con await son todos futuros por lo que correr a la vez pero asíncronamente 
                with faber.log_timer(completed):
                    for idx in range(0, issue_count):
                        await send(idx + 1) #manda credencial usando semaforo
                        if not (idx + 1) % batch_size and idx < issue_count - 1:
                            batch_timer.reset()

                await issue_task 
                await receive_task
            except KeyboardInterrupt:
                if receive_task:
                    receive_task.cancel()
                print("Cancelled")

        #Para el contador y muestra el tiempo medio por credencial/ping
        recv_timer.stop()
        avg = recv_timer.duration / issue_count
        item_short = "ping" if action == "ping" else "cred"
        item_long = "ping exchange" if action == "ping" else "credential"
        faber.log(f"Average time per {item_long}: {avg:.2f}s ({1/avg:.2f}/s)")
                
        #Revocación de credenciales en caso de que se quieran revocar
        if revoke_credentials and faber.revocations:
            with log_timer("Credentials revocation duration: "):
                log_msg("Starting credentials revocation")
                for rev_reg_id, cred_rev_id in faber.revocations:                   
                    await faber.revoke_credential(rev_reg_id, cred_rev_id,
                    not publish_revocations_at_once,faber.connection_id)
                    #en caso de no querer publicar las revocaciones al final todas juntas, se hace ahora
                    if not publish_revocations_at_once:
                        faber.log(
                            f"Revoking and publishing cred rev id {cred_rev_id} "
                            f"from rev reg id {rev_reg_id}"
                        )
                    else:
                        faber.log(f"Revoking but NO publishing cred rev id {cred_rev_id} "
                            f"from rev reg id {rev_reg_id}")
                if publish_revocations_at_once:
                    await faber.publish_revocations()
                    faber.log("Publishing all the credentials revocations at once")
        
        #Presentación de credenciales en caso de que se quieran mandar pruebas
        if proof_presentation:
            #Prepara los contadores               
            recv_timer = faber.log_timer(f"Completed {issue_count} proofs request exchanges in")
            batch_timer = faber.log_timer(f"Started {batch_size} proofs exchanges in")
        
            #Inicia contadores
            recv_timer.start()
            batch_timer.start()
            log_msg("Starting proof presentations")
            #Se crea una barra de progreso
            with progress() as pb:
                receive_task = None
                try:
    
                    #En primer lugar define la barra de la emisión, la barra de recepción, el tipo de accion y el tipo de funcion a usar (check_XXX)
                    issue_pg = pb(range(issue_count), label="Sending proofs requests") #barra emision 
                    receive_pg = pb(range(issue_count), label="Responding proof requests") #barra recepcion
                    check_received = check_received_proofs
                    send = send_proof
                    completed = f"Done sending {issue_count} proofs requests in" #texto a mostrar por el timer
    
                    issue_task = asyncio.ensure_future(
                        check_received(faber, issue_count, issue_pg)
                    ) # Creamos la tarea con objeto futuro para faber
                    issue_task.add_done_callback(faber.check_task_exception) #cuando acabe la tarea que llame a check_task_exception()
                    receive_task = asyncio.ensure_future(
                        check_received(alice, issue_count, receive_pg)
                    ) #hacemos lo mismo con alice
                    receive_task.add_done_callback(alice.check_task_exception)
    
                    #Las tres tareas con await son todos futuros por lo que correr a la vez pero asíncronamente
                    with faber.log_timer(completed):
                        for idx in range(0, issue_count):
                            await send(idx + 1) #manda credencial usando semaforo
                            if not (idx + 1) % batch_size and idx < issue_count - 1:
                                batch_timer.reset()
    
                    await issue_task 
                    await receive_task
                except KeyboardInterrupt:
                    if receive_task:
                        receive_task.cancel()
                    print("Cancelled")
    
            #Para el contador y muestra por log el tiempo medio por prueba
            recv_timer.stop()
            avg = recv_timer.duration / issue_count
            faber.log(f"Average time per proofs: {avg:.2f}s ({1/avg:.2f}/s)")
            
        if show_timing:
            timing = await alice.fetch_timing()
            if timing:
                for line in alice.format_timing(timing):
                    alice.log(line)

            timing = await faber.fetch_timing()
            if timing:
                for line in faber.format_timing(timing):
                    faber.log(line)
            if mediation:
                timing = await alice_mediator_agent.fetch_timing()
                if timing:
                    for line in alice_mediator_agent.format_timing(timing):
                        alice_mediator_agent.log(line)
                timing = await faber_mediator_agent.fetch_timing()
                if timing:
                    for line in faber_mediator_agent.format_timing(timing):
                        faber_mediator_agent.log(line)
        if alice.postgres:
            await alice.collect_postgres_stats(f"{issue_count} {item_short}s")
            for line in alice.format_postgres_stats():
                alice.log(line)
        if faber.postgres:
            await faber.collect_postgres_stats(f"{issue_count} {item_short}s")
            for line in faber.format_postgres_stats():
                faber.log(line)
    finally:
        terminated = True
        try:
            if alice:
                await alice.terminate()
        except Exception:
            LOGGER.exception("Error terminating agent:")
            terminated = False
        try:
            if faber:
                await faber.terminate()
        except Exception:
            LOGGER.exception("Error terminating agent:")
            terminated = False
        try:
            if alice_mediator_agent:
                await alice_mediator_agent.terminate()
            if faber_mediator_agent:
                await faber_mediator_agent.terminate()
        except Exception:
            LOGGER.exception("Error terminating agent:")
            terminated = False

    run_timer.stop()
    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Runs an automated credential issuance performance demo."
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=300,
        help="Set the number of credentials to issue",
    )
    parser.add_argument(
        "-b",
        "--batch",
        type=int,
        default=100,
        help="Set the batch size of credentials to issue",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8030,
        metavar=("<port>"),
        help="Choose the starting port number to listen on",
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        default=False,
        help="Only send ping messages between the agents",
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
        "--did-exchange",
        action="store_true",
        help="Use DID-Exchange protocol for connections",
    )
    parser.add_argument(
        "--proposal",
        action="store_true",
        default=False,
        help="Start credential exchange with a credential proposal from Alice",
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
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=10,
        help="Set the number of concurrent exchanges to start",
    )
    parser.add_argument(
        "--timing", action="store_true", help="Enable detailed timing report"
    )
    parser.add_argument(
        "--wallet-type",
        type=str,
        metavar="<wallet-type>",
        help="Set the agent wallet type",
    )
    parser.add_argument(
        "--arg-file",
        type=str,
        metavar="<arg-file>",
        help="Specify a file containing additional aca-py parameters",
    )
    args = parser.parse_args()

    #No es compatible mediación con did exchange
    if args.did_exchange and args.mediation:
        raise Exception(
            "DID-Exchange connection protocol is not (yet) compatible with mediation"
        )

    #inicializa la url del servidor tails
    tails_server_base_url = args.tails_server_base_url or os.getenv("PUBLIC_TAILS_URL")

    #recuerda especificar la url del servidor en caso de no haberlo hecho
    if args.revocation and not tails_server_base_url:
        raise Exception(
            "If revocation is enabled, --tails-server-base-url must be provided"
        )
    action = "issue"

    #si se quieren mandar proposiciones
    if args.proposal:
        action = "propose"
    #si se quiere mandar pings
    if args.ping:
        action = "ping"

    #comprueba los requirimientos de indy, aries, ursa...
    check_requires(args)


    try:
        asyncio.get_event_loop().run_until_complete(
            main(
                args.port,
                args.threads,
                action,
                args.timing,
                args.multitenant,
                args.mediation,
                args.multi_ledger,
                args.did_exchange,
                args.revocation,
                tails_server_base_url,
                args.count,
                args.batch,
                args.wallet_type,
                args.arg_file,
                args.proof_presentation,
                args.revoke_credentials,
                args.publish_revocations_at_once,
            )
        )
    except KeyboardInterrupt:
        os._exit(1)
