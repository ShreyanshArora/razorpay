"""Synthetic payments-world generator for NEXUS.

Design principle (this is what makes the whole eval honest):
we generate FOUR populations, and the interesting difficulty is deliberate.

  1. NORMAL       independent customers, unique identifiers, spread-out timing.
  2. RING_OBVIOUS fraud rings that SHARE hard identifiers (device/card/address).
                  -> a GROUP BY would catch these. They exist so the graph layer
                     has easy wins and so the demo has clear pictures.
  3. RING_EVASIVE fraud rings that ROTATE identifiers (fresh device/IP/card per
                  account) and betray themselves ONLY through behaviour:
                  tight account-creation + transaction timing, amount structuring
                  just under a threshold, high velocity, later disputes.
                  -> a JOIN CANNOT catch these. This is where graph+ML earns its keep.
  4. LOOKALIKE    legitimate clusters that LOOK coordinated and are the false-positive
                  traps: families (shared home device/address), offices (shared IP,
                  unrelated people), resellers (one person, many orders, shared card).

Ground-truth labels (Population, ring_id) are attached but MUST only be used by the
eval harness — never fed to the detector.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from nexus.schema import (
    Account, Transaction, World, Population, LookalikeKind,
)

# Structuring threshold fraudsters try to stay under (mirrors real "just under a limit").
STRUCTURING_THRESHOLD = 5000.0
BASE_TIME = datetime(2026, 8, 1, 0, 0, 0)


class WorldGenerator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self._acc_n = 0
        self._txn_n = 0
        self._dev_n = 0
        self._ip_n = 0
        self._card_n = 0
        self._addr_n = 0

    # ---- id helpers ----
    def _acc(self) -> str:
        self._acc_n += 1; return f"acc_{self._acc_n:05d}"
    def _txn(self) -> str:
        self._txn_n += 1; return f"txn_{self._txn_n:06d}"
    def _dev(self) -> str:
        self._dev_n += 1; return f"dev_{self._dev_n:05d}"
    def _ip(self) -> str:
        self._ip_n += 1; return f"ip_{self._ip_n:05d}"
    def _card(self) -> str:
        self._card_n += 1; return f"card_{self._card_n:05d}"
    def _addr(self) -> str:
        self._addr_n += 1; return f"addr_{self._addr_n:05d}"

    def _minutes(self, base: datetime, lo: float, hi: float) -> datetime:
        return base + timedelta(minutes=self.rng.uniform(lo, hi))

    # ---------------------------------------------------------------- NORMAL
    def _gen_normal(self, n_accounts: int, out_acc, out_txn):
        for _ in range(n_accounts):
            aid = self._acc()
            created = BASE_TIME + timedelta(days=self.rng.uniform(0, 25))
            out_acc.append(Account(aid, created, Population.NORMAL))
            device, ip, card, addr = self._dev(), self._ip(), self._card(), self._addr()
            for _ in range(self.rng.randint(1, 4)):
                t = created + timedelta(days=self.rng.uniform(0, 30),
                                        minutes=self.rng.uniform(0, 1440))
                out_txn.append(Transaction(
                    self._txn(), aid,
                    amount=round(self.rng.uniform(200, 20000), 2),
                    created_at=t,
                    device_id=device if self.rng.random() < 0.85 else self._dev(),
                    ip_id=ip if self.rng.random() < 0.7 else self._ip(),
                    card_fingerprint=card,
                    shipping_address_id=addr,
                    status="captured" if self.rng.random() < 0.94 else "failed",
                    disputed=self.rng.random() < 0.004,
                    population=Population.NORMAL,
                ))

    # ----------------------------------------------------------- RING_OBVIOUS
    def _gen_ring_obvious(self, ring_id: str, size: int, out_acc, out_txn):
        # A few shared devices/cards/addresses across all accounts.
        devices = [self._dev() for _ in range(self.rng.randint(2, 3))]
        cards = [self._card() for _ in range(self.rng.randint(1, 2))]
        addr = self._addr()
        ips = [self._ip() for _ in range(self.rng.randint(1, 2))]
        burst_start = BASE_TIME + timedelta(days=self.rng.uniform(1, 24))
        for _ in range(size):
            aid = self._acc()
            created = self._minutes(burst_start, 0, 20)  # accounts created within ~20 min
            out_acc.append(Account(aid, created, Population.RING_OBVIOUS, ring_id=ring_id))
            for _ in range(self.rng.randint(1, 3)):
                t = self._minutes(burst_start, 0, 12)     # transactions within ~12 min
                out_txn.append(Transaction(
                    self._txn(), aid,
                    amount=round(self.rng.uniform(4000, 6000), 2),
                    created_at=t,
                    device_id=self.rng.choice(devices),
                    ip_id=self.rng.choice(ips),
                    card_fingerprint=self.rng.choice(cards),
                    shipping_address_id=addr,
                    status="captured" if self.rng.random() < 0.9 else "failed",
                    disputed=self.rng.random() < 0.55,     # rings dispute a lot later
                    population=Population.RING_OBVIOUS, ring_id=ring_id,
                ))

    # ----------------------------------------------------------- RING_EVASIVE
    def _gen_ring_evasive(self, ring_id: str, size: int, out_acc, out_txn):
        # NO shared hard identifiers: fresh device/ip/card/addr per account.
        # Betrayed ONLY by behaviour: tight timing, amount structuring, velocity, disputes.
        burst_start = BASE_TIME + timedelta(days=self.rng.uniform(1, 24))
        # tight but not identical creation window
        for i in range(size):
            aid = self._acc()
            created = self._minutes(burst_start, i * 0.5, i * 0.5 + 6)
            out_acc.append(Account(aid, created, Population.RING_EVASIVE, ring_id=ring_id))
            n_txn = self.rng.randint(1, 2)
            # ~20% of ring members are "quiet mules": weaker signal (realistic noise)
            quiet = self.rng.random() < 0.20
            for _ in range(n_txn):
                # structuring: amounts cluster just under the threshold (quiet ones stray)
                if quiet:
                    amt = round(self.rng.uniform(2000, 9000), 2)
                    t = self._minutes(burst_start, i * 0.5, i * 0.5 + 40)
                else:
                    amt = round(STRUCTURING_THRESHOLD - self.rng.uniform(1, 250), 2)
                    t = self._minutes(burst_start, i * 0.5, i * 0.5 + 8)
                out_txn.append(Transaction(
                    self._txn(), aid,
                    amount=amt,
                    created_at=t,
                    device_id=self._dev(),        # unique — rotated
                    ip_id=self._ip(),             # unique — rotated
                    card_fingerprint=self._card(),# unique — rotated
                    shipping_address_id=self._addr(),  # unique — rotated
                    status="captured" if self.rng.random() < 0.88 else "failed",
                    disputed=self.rng.random() < (0.12 if quiet else 0.55),
                    population=Population.RING_EVASIVE, ring_id=ring_id,
                ))

    # -------------------------------------------------------------- LOOKALIKE
    def _gen_lookalike(self, legit_id: str, kind: LookalikeKind, out_acc, out_txn):
        if kind == LookalikeKind.FAMILY:
            size = self.rng.randint(2, 4)  # strictly small — a household
            device = self._dev(); addr = self._addr(); ip = self._ip()
            cards = [self._card() for _ in range(size)]  # each person own card
            span_days = self.rng.uniform(20, 40)
            for i in range(size):
                aid = self._acc()
                created = BASE_TIME + timedelta(days=self.rng.uniform(0, span_days))
                out_acc.append(Account(aid, created, Population.LOOKALIKE,
                                       ring_id=legit_id, lookalike_kind=kind))
                for _ in range(self.rng.randint(1, 5)):
                    t = created + timedelta(days=self.rng.uniform(0, span_days))
                    out_txn.append(Transaction(
                        self._txn(), aid,
                        amount=round(self.rng.uniform(300, 15000), 2),
                        created_at=t,
                        device_id=device, ip_id=ip,
                        card_fingerprint=cards[i],
                        shipping_address_id=addr,
                        status="captured" if self.rng.random() < 0.95 else "failed",
                        disputed=self.rng.random() < 0.01,
                        population=Population.LOOKALIKE, ring_id=legit_id,
                    ))
        elif kind == LookalikeKind.OFFICE:
            size = self.rng.randint(8, 14)
            ip = self._ip()  # shared corporate IP — the ONLY shared thing
            span_days = self.rng.uniform(20, 45)
            for _ in range(size):
                aid = self._acc()
                created = BASE_TIME + timedelta(days=self.rng.uniform(0, span_days))
                out_acc.append(Account(aid, created, Population.LOOKALIKE,
                                       ring_id=legit_id, lookalike_kind=kind))
                # each coworker: own device, own card, own home address
                dev = self._dev(); card = self._card(); addr = self._addr()
                for _ in range(self.rng.randint(1, 4)):
                    t = created + timedelta(days=self.rng.uniform(0, span_days),
                                            minutes=self.rng.uniform(0, 600))
                    # ~15% of office txns come from home (fresh IP) — realistic noise
                    txn_ip = ip if self.rng.random() < 0.85 else self._ip()
                    out_txn.append(Transaction(
                        self._txn(), aid,
                        amount=round(self.rng.uniform(200, 18000), 2),
                        created_at=t, device_id=dev, ip_id=txn_ip,
                        card_fingerprint=card, shipping_address_id=addr,
                        status="captured" if self.rng.random() < 0.94 else "failed",
                        disputed=self.rng.random() < 0.01,
                        population=Population.LOOKALIKE, ring_id=legit_id,
                    ))
        else:  # RESELLER — one legit person, many orders, shared card/address
            aid = self._acc()
            created = BASE_TIME + timedelta(days=self.rng.uniform(0, 20))
            out_acc.append(Account(aid, created, Population.LOOKALIKE,
                                   ring_id=legit_id, lookalike_kind=kind))
            device = self._dev(); card = self._card(); addr = self._addr(); ip = self._ip()
            for _ in range(self.rng.randint(8, 20)):
                t = created + timedelta(days=self.rng.uniform(0, 30),
                                        minutes=self.rng.uniform(0, 1440))
                out_txn.append(Transaction(
                    self._txn(), aid,
                    amount=round(self.rng.uniform(500, 9000), 2),
                    created_at=t, device_id=device, ip_id=ip,
                    card_fingerprint=card, shipping_address_id=addr,
                    status="captured" if self.rng.random() < 0.96 else "failed",
                    disputed=self.rng.random() < 0.008,
                    population=Population.LOOKALIKE, ring_id=legit_id,
                ))

    # ------------------------------------------------------------------ build
    def generate(
        self,
        n_normal: int = 700,
        n_obvious_rings: int = 12,
        n_evasive_rings: int = 13,
        n_families: int = 20,
        n_offices: int = 8,
        n_resellers: int = 10,
        split: str = "dev",
    ) -> World:
        accs: list[Account] = []
        txns: list[Transaction] = []

        self._gen_normal(n_normal, accs, txns)
        for i in range(n_obvious_rings):
            self._gen_ring_obvious(f"ring_obv_{i:03d}", self.rng.randint(4, 10), accs, txns)
        for i in range(n_evasive_rings):
            self._gen_ring_evasive(f"ring_eva_{i:03d}", self.rng.randint(5, 12), accs, txns)
        for i in range(n_families):
            self._gen_lookalike(f"legit_fam_{i:03d}", LookalikeKind.FAMILY, accs, txns)
        for i in range(n_offices):
            self._gen_lookalike(f"legit_off_{i:03d}", LookalikeKind.OFFICE, accs, txns)
        for i in range(n_resellers):
            self._gen_lookalike(f"legit_res_{i:03d}", LookalikeKind.RESELLER, accs, txns)

        self.rng.shuffle(txns)
        return World(accounts=accs, transactions=txns, seed=self.seed, split=split)
