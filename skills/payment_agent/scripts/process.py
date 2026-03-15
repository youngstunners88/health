# skills/payment-agent/scripts/process.py
"""
Payment‑Agent skill – unified Celo + card / mobile‑wallet processor
with dynamic staking, tiered rewards, and sub‑pool splitting.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account
import requests   # for Stripe / Adyen / etc.

logger = logging.getLogger("payment_agent")

# ----------------------------------------------------------------------
# Configuration – load from env (you can also keep a .env file in the workspace)
# ----------------------------------------------------------------------
CELO_RPC_URL   = os.getenv("CELO_RPC_URL",   "https://alfajores-forno.celo-testnet.org")
CELO_CUSD_ADDR = os.getenv("CELO_CUSD_ADDR", "0x874069Fa1Eb16D44d622F2e0Ca25eeA172369bC1")   # cUSD testnet
# Three staking‑contract addresses (deploy same simple staking contract three times)
CELO_STAKING_FOLLOWUP   = os.getenv("CELO_STAKING_FOLLOWUP",   "0xYourFollowupPoolHere")
CELO_STAKING_WELLBEING  = os.getenv("CELO_STAKING_WELLBEING",  "0xYourWellbeingPoolHere")
CELO_STAKING_CLAIMFREE  = os.getenv("CELO_STAKING_CLAIMFREE",  "0xYourClaimFreePoolHere")

CELO_PRIVATE_KEY = os.getenv("CELO_PRIVATE_KEY")   # keeper account that signs txs
STATIC_STAKING_FRACTION = float(os.getenv("STATIC_STAKING_FRACTION", "0.05"))   # fallback 5 %

# Card gateway (Stripe example)
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_API_URL = "https://api.stripe.com/v1"

# ----------------------------------------------------------------------
# Web3 setup
# ----------------------------------------------------------------------
w3 = Web3(Web3.HTTPProvider(CELO_RPC_URL))
# Note: Connection check skipped in environments without RPC access; functions will handle connection errors at call time.

# Load ERC‑20 ABI for cUSD
with open(os.path.join(os.path.dirname(__file__), "..", "assets", "abi", "CeloERC20.json")) as f:
    ERC20_ABI = json.load(f)
celo_erc20 = w3.eth.contract(address=Web3.to_checksum_address(CELO_CUSD_ADDR), abi=ERC20_ABI)

# Load staking contract ABI (same for all three pools)
with open(os.path.join(os.path.dirname(__file__), "..", "assets", "abi", "CeloStaking.json")) as f:
    STAKING_ABI = json.load(f)

def _staking_contract(pool_address: str):
    return w3.eth.contract(address=Web3.to_checksum_address(pool_address), abi=STAKING_ABI)

# Account that will sign txs (ensure it has funds for gas)
if CELO_PRIVATE_KEY:
    acct = Account.from_key(CELO_PRIVATE_KEY)
    SENDER_ADDRESS = acct.address
else:
    SENDER_ADDRESS = None   # you can fall back to a meta‑transaction relayer if needed

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def _celo_transfer(amount_wei: int, to_address: str) -> Dict[str, Any]:
    nonce = w3.eth.get_transaction_count(SENDER_ADDRESS)
    txn = celo_erc20.functions.transfer(
        Web3.to_checksum_address(to_address),
        amount_wei
    ).buildTransaction({
        "chainId": w3.eth.chain_id,
        "gas": 100000,
        "gasPrice": w3.toWei('2', 'gwei'),
        "nonce": nonce,
    })
    signed = acct.sign_transaction(txn)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return {"status": "success" if receipt.status == 1 else "failed",
            "tx_hash": tx_hash.hex(),
            "receipt": receipt}

def _stake(amount_wei: int, pool_address: str) -> Dict[str, Any]:
    """Deposit amount into the given staking contract."""
    contract = _staking_contract(pool_address)
    nonce = w3.eth.get_transaction_count(SENDER_ADDRESS)
    txn = contract.functions.deposit(amount_wei).buildTransaction({
        "chainId": w3.eth.chain_id,
        "gas": 80000,
        "gasPrice": w3.toWei('2', 'gwei'),
        "nonce": nonce,
    })
    signed = acct.sign_transaction(txn)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return {"status": "success" if receipt.status == 1 else "failed",
            "tx_hash": tx_hash.hex(),
            "receipt": receipt}

def _get_pending_reward(pool_address: str) -> int:
    """Return pending reward (in wei) for the signer address."""
    contract = _staking_contract(pool_address)
    return contract.functions.getPendingReward(SENDER_ADDRESS).call()

def _charge_card(amount_cents: int, currency: str, metadata: dict) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {STRIPE_API_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "amount": amount_cents,
        "currency": currency.lower(),
        "description": f"Health‑care payment {metadata.get('patient_id','?')}",
    }
    resp = requests.post(f"{STRIPE_API_URL}/charge", headers=headers, data=data, timeout=10)
    data = resp.json()
    if data.get("paid"):
        return {
            "status": "success",
            "gateway_response": data,
            "receipt": f"Card {currency.upper()} ${amount_cents/100:.2f} charged (id {data['id']})"
        }
    else:
        return {
            "status": "failed",
            "gateway_response": data,
            "receipt": f"Card charge failed: {data.get('error', {}).get('message', 'unknown')}"
        }

def _reward_multiplier(adherence_days: Optional[int]) -> float:
    """
    Tiered reward multiplier based on claim‑free streak.
    0‑30 days  → 1.0× (base APY)
    31‑90 days → 1.2×
    >90 days   → 1.5×
    """
    if adherence_days is None:
        return 1.0
    if adherence_days <= 30:
        return 1.0
    if adherence_days <= 90:
        return 1.2
    return 1.5

def _pool_for_purpose(purpose: str) -> str:
    """
    Map a purpose string to a staking‑contract address.
    Deploy three copies of the simple staking contract and set the env vars:
      CELO_STAKING_FOLLOWUP, CELO_STAKING_WELLBEING, CELO_STAKING_CLAIMFREE
    """
    purpose = purpose.lower().replace(" ", "_")
    if purpose == "follow_up_bonus":
        return CELO_STAKING_FOLLOWUP
    if purpose == "wellbeing_incentive":
        return CELO_STAKING_WELLBEING
    if purpose == "claim_free_rebate":
        return CELO_STAKING_CLAIMFREE
    # Fallback to the first pool if unknown
    logger.warning(f"Unknown staking purpose '{purpose}', defaulting to follow‑up pool")
    return CELO_STAKING_FOLLOWUP

def _build_receipt(status: str, amount: float, currency: str, method: str,
                   tx_hash: str | None, gateway_resp: dict | None,
                   metadata: dict) -> str:
    lines = [
        f"Payment {status.upper()}",
        f"Amount: {amount:.2f} {currency.upper()}",
        f"Method: {method}",
        f"Patient ID: {metadata.get('patient_id','-')}",
    ]
    if tx_hash:
        lines.append(f"Tx hash: {tx_hash}")
    if gateway_resp:
        lines.append(f"Gateway ID: {gateway_resp.get('id','-')}")
    lines.append(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    return "\n".join(lines)

# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def pay(amount: float,
        currency: str,
        method: str,
        metadata: dict | None = None,
        risk_score: Optional[float] = None,
        adherence_days: Optional[int] = None,
        purpose: str = "follow_up_bonus") -> Dict[str, Any]:
    """
    Main entry point for the skill.

    Parameters
    ----------
    amount : float
        Amount in the *unit* of the currency (e.g., 10.00 = ten dollars or ten cUSD).
    currency : str
        "celo-usd", "celo-eur", "usd", "eur".
    method : str
        "celo", "card", "apple-pay", "google-pay".
    metadata : dict, optional
        Arbitrary data (patient_id, procedure, insurance‑eligibility, etc.).
    risk_score : float, optional
        0.0‑1.0 representing the patient’s risk (0 = low risk, 1 = high risk).
        Used to compute a dynamic staking fraction.
    adherence_days : int, optional
        Number of consecutive days the patient has been claim‑free.
        Drives the tiered‑reward multiplier.
    purpose : str, default "follow_up_bonus"
        Which staking sub‑pool to deposit into.
          Options: "follow_up_bonus", "wellbeing_incentive", "claim_free_rebate".
    """
    if metadata is None:
        metadata = {}

    # Normalise inputs
    currency = currency.lower()
    method   = method.lower()

    # Convert amount to smallest integer unit
    if currency.startswith("celo"):   # cUSD/CEUR have 18 decimals like ERC‑20
        amount_small = int(round(amount * 10**18))
    else:                              # fiat currencies – 2 decimal places (cents)
        amount_small = int(round(amount * 100))

    # ------------------------------------------------------------------
    # 1️⃣ Execute the payment (blockchain or card)
    # ------------------------------------------------------------------
    if method == "celo":
        # For demo we send to the keeper address; replace with a treasury or escrow if needed.
        res = _celo_transfer(amount_small, SENDER_ADDRESS)
        tx_hash = res.get("tx_hash") if res["status"] == "success" else None
        gateway_resp = None
    elif method in ("card", "apple-pay", "google-pay"):
        # Treat all three as a simple card charge for the hackathon.
        res = _charge_card(amount_small // 100,   # convert wei→cents for fiat
                           currency.split("-")[0] if "-" in currency else currency,
                           metadata)
        tx_hash = None
        gateway_resp = res.get("gateway_response")
    else:
        return {
            "status": "failed",
            "tx_hash": None,
            "gateway_response": None,
            "receipt": f"Unsupported payment method: {method}"
        }

    # ------------------------------------------------------------------
    # 2️⃣ Determine dynamic staking fraction (if risk_score supplied)
    # ------------------------------------------------------------------
    base_frac = STATIC_STAKING_FRACTION
    if risk_score is not None:
        # Example curve: low risk → higher fraction, high risk → lower fraction
        # Clamp to [0.01, 0.10] so we never stake nothing or too much.
        dynamic_frac = max(0.01, min(0.10, base_frac * (1.0 - risk_score)))
    else:
        dynamic_frac = base_frac

    # ------------------------------------------------------------------
    # 3️⃣ Compute staking amount (wei) and apply tiered multiplier later
    # ------------------------------------------------------------------
    stake_amount = int(amount_small * dynamic_frac)
    staking_tx = None
    pending_reward_wei = 0
    expected_yield_wei = 0   # placeholder for quantum‑finance consumption

    if method == "celo" and res.get("status") == "success" and stake_amount > 0:
        pool_addr = _pool_for_purpose(purpose)
        staking_res = _stake(stake_amount, pool_addr)
        if staking_res.get("status") == "success":
            staking_tx = staking_res.get("tx_hash")
            # Query pending reward (includes any accrued yield)
            pending_reward_wei = _get_pending_reward(pool_addr)
            # Expected yield = stake * APY * multiplier.
            # Here we pull a rough APY from an env var (you can also query an oracle).
            base_apy = float(os.getenv("STAKING_APY", "0.02"))   # 2 % annual as default
            multiplier = _reward_multiplier(adherence_days)
            expected_yield_wei = int(stake_amount * base_apy * multiplier)
            logger.info(
                f"Staked {stake_amount} wei into pool {purpose} "
                f"(fraction={dynamic_frac:.4f}, multiplier={multiplier:.2f})"
            )
        else:
            logger.warning(f"Staking transaction failed: {staking_res}")

    # ------------------------------------------------------------------
    # 4️⃣ Build receipt
    # ------------------------------------------------------------------
    receipt = _build_receipt(
        status=res.get("status", "failed"),
        amount=amount,
        currency=currency.upper(),
        method=method,
        tx_hash=tx_hash,
        gateway_resp=gateway_resp,
        metadata=metadata
    )

    # ------------------------------------------------------------------
    # 5️⃣ Return enriched result for orchestrator / quantum‑finance
    # ------------------------------------------------------------------
    return {
        "status": res.get("status", "failed"),
        "tx_hash": tx_hash,
        "gateway_response": gateway_resp,
        "receipt": receipt,
        # ---- New fields for the enhancements ----
        "staking_tx": staking_tx,
        "staking_pool": purpose,
        "staking_fraction_used": dynamic_frac,
        "staking_amount_wei": stake_amount,
        "pending_reward_wei": pending_reward_wei,
        "expected_yield_wei": expected_yield_wei,   # deterministic cash‑inflow for quantum‑finance
        "reward_multiplier": _reward_multiplier(adherence_days),
    }

# ----------------------------------------------------------------------
# Exported symbols
# ----------------------------------------------------------------------
__all__ = ["pay"]
