import smartpy as sp


class Marketplace(sp.Contract):
    def __init__(self, objkt, metadata, manager, fee):
        self.init(
            metadata = metadata,
            manager = manager,
            fee_recipient = manager,
            allowed_fa2s = sp.set([objkt]),
            swaps = sp.big_map(
                tkey=sp.TNat,
                tvalue=sp.TRecord(
                    issuer=sp.TAddress,
                    fa2=sp.TAddress,
                    objkt_amount=sp.TNat,
                    objkt_id=sp.TNat,
                    xtz_per_objkt=sp.TMutez,
                    royalties=sp.TNat,
                    creator=sp.TAddress)),
            counter = 500000,
            fee = fee)

    @sp.entry_point
    def swap(self, params):
        sp.verify(self.data.allowed_fa2s.contains(params.fa2))
        sp.verify((params.objkt_amount > 0) & ((params.royalties >= 0) & (params.royalties <= 250)))
        self.fa2_transfer(params.fa2, sp.sender, sp.self_address, params.objkt_id, params.objkt_amount)
        self.data.swaps[self.data.counter] = sp.record(
            issuer=sp.sender,
            fa2=params.fa2,
            objkt_amount=params.objkt_amount,
            objkt_id=params.objkt_id,
            xtz_per_objkt=params.xtz_per_objkt,
            royalties=params.royalties,
            creator=params.creator)
        self.data.counter += 1

    @sp.entry_point
    def collect(self, params):
        # verifies if tez amount is equal to price per objkt
        sp.verify(
            (sp.amount == self.data.swaps[params.swap_id].xtz_per_objkt) & 
            (self.data.swaps[params.swap_id].objkt_amount != 0))

        sp.if (self.data.swaps[params.swap_id].xtz_per_objkt != sp.tez(0)):
            # Send the royalties to the NFT creator
            self.royalties_amount = sp.split_tokens(
                self.data.swaps[params.swap_id].xtz_per_objkt, self.data.swaps[params.swap_id].royalties, 1000)

            sp.if (self.royalties_amount > sp.mutez(0)):
                sp.send(self.data.swaps[params.swap_id].creator, self.royalties_amount)

            # Send the management fees
            self.fee_amount = sp.split_tokens(
                self.data.swaps[params.swap_id].xtz_per_objkt, self.data.fee, 1000)

            sp.if (self.fee_amount > sp.mutez(0)):
                sp.send(self.data.fee_recipient, self.fee_amount)

            # Send the rest to the issuer
            sp.send(
                self.data.swaps[params.swap_id].issuer,
                sp.amount - self.royalties_amount - self.fee_amount)

        self.data.swaps[params.swap_id].objkt_amount = sp.as_nat(self.data.swaps[params.swap_id].objkt_amount - 1)

        self.fa2_transfer(
            self.data.swaps[params.swap_id].fa2,
            sp.self_address,
            sp.sender,
            self.data.swaps[params.swap_id].objkt_id,
            1)

    @sp.entry_point
    def cancel_swap(self, params):
        sp.verify(
            (sp.sender == self.data.swaps[params].issuer) & 
            (self.data.swaps[params].objkt_amount != 0))
        self.fa2_transfer(
            self.data.swaps[params].fa2,
            sp.self_address,
            sp.sender,
            self.data.swaps[params].objkt_id,
            self.data.swaps[params].objkt_amount)
        del self.data.swaps[params]

    @sp.entry_point
    def update_fee(self, params):
        sp.verify(sp.sender == self.data.manager)
        sp.verify(params <= 250)
        self.data.fee = params

    @sp.entry_point
    def update_fee_recipient(self, params):
        sp.verify(sp.sender == self.data.manager)
        self.data.fee_recipient = params

    @sp.entry_point
    def update_manager(self, params):
        sp.verify(sp.sender == self.data.manager)
        self.data.manager = params

    @sp.entry_point
    def add_fa2_address(self, params):
        sp.verify(sp.sender == self.data.manager)
        self.data.allowed_fa2s.add(params)

    @sp.entry_point
    def remove_fa2_address(self, params):
        sp.verify(sp.sender == self.data.manager)
        self.data.allowed_fa2s.remove(params)

    def fa2_transfer(self, fa2, from_, to_, objkt_id, objkt_amount):
        c = sp.contract(
            sp.TList(sp.TRecord(
                from_=sp.TAddress,
                txs=sp.TList(sp.TRecord(
                    amount=sp.TNat,
                    to_=sp.TAddress,
                    token_id=sp.TNat).layout(("to_", ("token_id", "amount")))))),
            fa2,
            entry_point="transfer").open_some()
        sp.transfer(
            sp.list([sp.record(
                from_=from_,
                txs=sp.list([sp.record(
                    amount=objkt_amount,
                    to_=to_,
                    token_id=objkt_id)]))]),
            sp.mutez(0), c)
