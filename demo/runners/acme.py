import asyncio
import json
import logging
import os
import sys
import time
import datetime
from aiohttp import ClientError
from qrcode import QRCode


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa

from runners.agent_container import (  # noqa:E402
    arg_parser,
    create_agent_with_args,
    AriesAgent,
)
from runners.support.agent import (  # noqa:E402
    CRED_FORMAT_INDY,
    CRED_FORMAT_JSON_LD,
    SIG_TYPE_BLS,
)
from runners.support.utils import (  # noqa:E402
    check_requires,
    log_msg,
    log_status,
    log_timer,
    prompt,
    prompt_loop,
)


CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview"
SELF_ATTESTED = os.getenv("SELF_ATTESTED")
TAILS_FILE_COUNT = int(os.getenv("TAILS_FILE_COUNT", 100))

logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


class AcmeAgent(AriesAgent):
    def __init__(
        self,
        ident: str,
        http_port: int,
        admin_port: int,
        no_auto: bool = False,
        **kwargs,
    ):
        super().__init__(
            ident,
            http_port,
            admin_port,
            prefix="Acme",
            no_auto=no_auto,
            **kwargs,
        )
        self.connection_id = None
        self._connection_ready = None
        self.cred_state = {}
        self.cred_attrs = {}

    async def detect_connection(self):
        await self._connection_ready
        self._connection_ready = None

    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()
    '''
    async def handle_oob_invitation(self, message):
        pass

    async def handle_connections(self, message):
        print(
            self.ident, "handle_connections", message["state"], message["rfc23_state"]
        )
        conn_id = message["connection_id"]
        if (not self.connection_id) and message["rfc23_state"] == "invitation-sent":
            print(self.ident, "set connection id", conn_id)
            self.connection_id = conn_id
        if (
            message["connection_id"] == self.connection_id
            and message["rfc23_state"] == "completed"
            and (self._connection_ready and not self._connection_ready.done())
        ):
            self.log("Connected")
            self._connection_ready.set_result(True)

    async def handle_issue_credential_v2_0(self, message):
        state = message["state"]
        cred_ex_id = message["cred_ex_id"]
        prev_state = self.cred_state.get(cred_ex_id)
        if prev_state == state:
            return  # ignore
        self.cred_state[cred_ex_id] = state

        self.log(f"Credential: state = {state}, cred_ex_id = {cred_ex_id}")

        if state == "request-received":
            # TODO issue credentials based on offer preview in cred ex record
            pass

    async def handle_issue_credential_v2_0_indy(self, message):
        pass  # employee id schema does not support revocation

    async def handle_present_proof_v2_0(self, message):
        state = message["state"]
        pres_ex_id = message["pres_ex_id"]
        self.log(f"Presentation: state = {state}, pres_ex_id = {pres_ex_id}")

        if state == "presentation-received":
            # TODO handle received presentations
            pass

    async def handle_basicmessages(self, message):
        self.log("Received message:", message["content"])
    '''
    def generate_credential_offer(self, aip, cred_type, cred_def_id, exchange_tracing):
        if aip == 10:
            # define attributes to send for credential
            self.cred_attrs[cred_def_id] = {
                "employee_id": "ACME009",
                "name": "Alice Smith",
                "date": "2022-05-28",
                "position": "CEO",
            }

            cred_preview = {
                "@type": CRED_PREVIEW_TYPE,
                "attributes": [
                    {"name": n, "value": v}
                    for (n, v) in self.cred_attrs[cred_def_id].items()
                ],
            }
            offer_request = {
                "connection_id": self.connection_id,
                "cred_def_id": cred_def_id,
                "comment": f"Offer on cred def id {cred_def_id}",
                "auto_remove": False,
                "credential_preview": cred_preview,
                "trace": exchange_tracing,
            }
            return offer_request

        elif aip == 20:
            if cred_type == CRED_FORMAT_INDY:
                self.cred_attrs[cred_def_id] = {
                    "employee_id": "ACME009",
                    "name": "Alice Smith",
                    "date": "2022-05-28",
                    "position": "CEO",
                }

                cred_preview = {
                    "@type": CRED_PREVIEW_TYPE,
                    "attributes": [
                        {"name": n, "value": v}
                        for (n, v) in self.cred_attrs[cred_def_id].items()
                    ],
                }
                offer_request = {
                    "connection_id": self.connection_id,
                    "comment": f"Offer on cred def id {cred_def_id}",
                    "auto_remove": False,
                    "credential_preview": cred_preview,
                    "filter": {"indy": {"cred_def_id": cred_def_id}},
                    "trace": exchange_tracing,
                }
                return offer_request

            elif cred_type == CRED_FORMAT_JSON_LD:
                offer_request = {
                    "connection_id": self.connection_id,
                    "filter": {
                        "ld_proof": {
                            "credential": {
                                "@context": [
                                    "https://www.w3.org/2018/credentials/v1",
                                    "https://w3id.org/citizenship/v1",
                                    "https://w3id.org/security/bbs/v1",
                                ],
                                "type": [
                                    "VerifiableCredential",
                                    "PermanentResident",
                                ],
                                "id": "https://credential.example.com/residents/1234567890",
                                "issuer": self.did,
                                "issuanceDate": "2020-01-01T12:00:00Z",
                                "credentialSubject": {
                                    "type": ["PermanentResident"],
                                    "givenName": "ALICE",
                                    "familyName": "SMITH",
                                    "gender": "Female",
                                    "birthCountry": "Bahamas",
                                    "birthDate": "1958-07-17",
                                },
                            },
                            "options": {"proofType": SIG_TYPE_BLS},
                        }
                    },
                }
                return offer_request

            else:
                raise Exception(f"Error invalid credential type: {self.cred_type}")

        else:
            raise Exception(f"Error invalid AIP level: {self.aip}")

    def generate_proof_request_web_request(
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


async def main(args):
    acme_agent = await create_agent_with_args(args, ident="acme")

    try:
        log_status(
            "#1 Provision an agent and wallet, get back configuration details"
            + (
                f" (Wallet type: {acme_agent.wallet_type})"
                if acme_agent.wallet_type
                else ""
            )
        )
        agent = AcmeAgent(
            "acme.agent",
            acme_agent.start_port,
            acme_agent.start_port + 1,
            genesis_data=acme_agent.genesis_txns,
            genesis_txn_list=acme_agent.genesis_txn_list,
            no_auto=acme_agent.no_auto,
            tails_server_base_url=acme_agent.tails_server_base_url,
            timing=acme_agent.show_timing,
            multitenant=acme_agent.multitenant,
            mediation=acme_agent.mediation,
            wallet_type=acme_agent.wallet_type,
            seed=acme_agent.seed,
        )

        acme_agent.public_did = True
        acme_schema_name = "employee id schema"
        acme_schema_attrs = ["employee_id", "name", "date", "position"]
        await acme_agent.initialize(
            the_agent=agent,
            schema_name=acme_schema_name,
            schema_attrs=acme_schema_attrs,
            create_endorser_agent=(acme_agent.endorser_role == "author")
                if acme_agent.endorser_role
                else False,
        )

        # TODO publish schema and cred def

        # generate an invitation for Alice
        await acme_agent.generate_invitation(display_qr=True, reuse_connections=acme_agent.reuse_connections, wait=True)

        exchange_tracing = False
        options = (
            "    (1) Issue Credential\n"
            "    (2) Send Proof Request\n"
            "    (3) Send Message\n"
            "    (X) Exit?\n"
            "[1/2/3/X]"
        )
        async for option in prompt_loop(options):
            if option is not None:
                option = option.strip()

            if option is None or option in "xX":
                break

            elif option == "1":
                log_status("#13 Issue credential offer to X")
                if acme_agent.aip == 10:
                    offer_request = acme_agent.agent.generate_credential_offer(
                        acme_agent.aip, None, acme_agent.cred_def_id, exchange_tracing
                    )
                    await acme_agent.agent.admin_POST(
                        "/issue-credential/send-offer", offer_request
                    )

                elif acme_agent.aip == 20:
                    if acme_agent.cred_type == CRED_FORMAT_INDY:
                        offer_request = acme_agent.agent.generate_credential_offer(
                            acme_agent.aip,
                            acme_agent.cred_type,
                            acme_agent.cred_def_id,
                            exchange_tracing,
                        )

                    elif acme_agent.cred_type == CRED_FORMAT_JSON_LD:
                        offer_request = acme_agent.agent.generate_credential_offer(
                            acme_agent.aip,
                            acme_agent.cred_type,
                            None,
                            exchange_tracing,
                        )

                    else:
                        raise Exception(
                            f"Error invalid credential type: {acme_agent.cred_type}"
                        )

                    await acme_agent.agent.admin_POST(
                        "/issue-credential-2.0/send-offer", offer_request
                    )

                else:
                    raise Exception(f"Error invalid AIP level: {acme_agent.aip}")


            elif option == "2":
                log_status("#20 Request proof of degree from alice")
                if acme_agent.aip == 10:
                    proof_request_web_request = (
                        acme_agent.agent.generate_proof_request_web_request(
                            acme_agent.aip,
                            acme_agent.cred_type,
                            acme_agent.revocation,
                            exchange_tracing,
                        )
                    )
                    await acme_agent.agent.admin_POST(
                        "/present-proof/send-request", proof_request_web_request
                    )
                    pass

                elif acme_agent.aip == 20:
                    if acme_agent.cred_type == CRED_FORMAT_INDY:
                        proof_request_web_request = (
                            acme_agent.agent.generate_proof_request_web_request(
                                acme_agent.aip,
                                acme_agent.cred_type,
                                acme_agent.revocation,
                                exchange_tracing,
                            )
                        )

                    elif acme_agent.cred_type == CRED_FORMAT_JSON_LD:
                        proof_request_web_request = (
                            acme_agent.agent.generate_proof_request_web_request(
                                acme_agent.aip,
                                acme_agent.cred_type,
                                acme_agent.revocation,
                                exchange_tracing,
                            )
                        )

                    else:
                        raise Exception(
                            "Error invalid credential type:" + acme_agent.cred_type
                        )

                    await agent.admin_POST(
                        "/present-proof-2.0/send-request", proof_request_web_request
                    )

                else:
                    raise Exception(f"Error invalid AIP level: {acme_agent.aip}")

            elif option == "3":
                msg = await prompt("Enter message: ")
                await agent.admin_POST(
                    f"/connections/{agent.connection_id}/send-message", {"content": msg}
                )

        if acme_agent.show_timing:
            timing = await acme_agent.agent.fetch_timing()
            if timing:
                for line in acme_agent.agent.format_timing(timing):
                    log_msg(line)

    finally:
        terminated = await acme_agent.terminate()

    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)


if __name__ == "__main__":
    parser = arg_parser(ident="acme", port=8040)
    args = parser.parse_args()

    ENABLE_PYDEVD_PYCHARM = os.getenv("ENABLE_PYDEVD_PYCHARM", "").lower()
    ENABLE_PYDEVD_PYCHARM = ENABLE_PYDEVD_PYCHARM and ENABLE_PYDEVD_PYCHARM not in (
        "false",
        "0",
    )
    PYDEVD_PYCHARM_HOST = os.getenv("PYDEVD_PYCHARM_HOST", "localhost")
    PYDEVD_PYCHARM_CONTROLLER_PORT = int(
        os.getenv("PYDEVD_PYCHARM_CONTROLLER_PORT", 5001)
    )

    if ENABLE_PYDEVD_PYCHARM:
        try:
            import pydevd_pycharm

            print(
                "Acme remote debugging to "
                f"{PYDEVD_PYCHARM_HOST}:{PYDEVD_PYCHARM_CONTROLLER_PORT}"
            )
            pydevd_pycharm.settrace(
                host=PYDEVD_PYCHARM_HOST,
                port=PYDEVD_PYCHARM_CONTROLLER_PORT,
                stdoutToServer=True,
                stderrToServer=True,
                suspend=False,
            )
        except ImportError:
            print("pydevd_pycharm library was not found")

    check_requires(args)

    try:
        asyncio.get_event_loop().run_until_complete(main(args))
    except KeyboardInterrupt:
        os._exit(1)
