from fastapi import APIRouter
from pydantic import BaseModel

from blockchain.scripts.addRecord import add

router = APIRouter(prefix="/payout", tags=["payout"])


class PayoutRequest(BaseModel):
    farmer: str   # mongo id coming here
    scheme: str
    amount: int
    txnid: str


def convert_to_eth_address(farmer_id: str) -> str:
    """
    Convert mongo id (24 hex) → valid 20-byte ETH address
    """
    clean = farmer_id.lower().replace("0x", "")

    # pad to 40 hex chars
    padded = clean.ljust(40, "0")[:40]

    return "0x" + padded


@router.post("/send")
def send_payout(data: PayoutRequest):

    eth_farmer_address = convert_to_eth_address(data.farmer)

    add(
        eth_farmer_address,
        data.scheme,
        data.amount,
        data.txnid
    )

    return {
        "status": "success",
        "farmer_wallet": eth_farmer_address,
        "message": "Transaction sent to blockchain"
    }
