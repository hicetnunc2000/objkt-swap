class Marketplace(sp.Contract):
    def __init__(self, objkt, metadata, manager):
        self.init(
            objkt = objkt,
            metadata = metadata,
            manager = manager,
            swaps = sp.big_map(tkey=sp.TNat, tvalue=sp.TRecord(issuer=sp.TAddress, objkt_amount=sp.TNat, objkt_id=sp.TNat, xtz_per_objkt=sp.TMutez, royalties=sp.TNat, creator=sp.TAddress)),
            counter = 0
            )
            
    @sp.entry_point
    def swap(self, params):
        self.fa2_transfer(self.data.objkt, sp.sender, sp.self_address, params.objkt_id, params.objkt_amount)
        self.data.swaps[self.data.counter] = sp.record(issuer=sp.sender, objkt_amount=params.objkt_amount, objkt_id=params.objkt_id, xtz_per_objkt=params.xtz_per_objkt, royalties=params.royalties, creator=params.creator)
        self.data.counter += 1
    
    @sp.entry_point
    def collect(self, params):
        sp.verify(
            # verifies if tez amount is equal to objkts amount * price per objkt
            (sp.amount == sp.utils.nat_to_mutez(params.objkt_amount * sp.fst(sp.ediv(self.data.swaps[params.swap_id].xtz_per_objkt, sp.mutez(1)).open_some()))) 
            # exploit solution
            & (abs(self.data.swaps[params.swap_id].objkt_amount - params.objkt_amount) >= 0)
            & (self.data.swaps[params.swap_id].objkt_amount != 0)
            )

        self.amount = params.objkt_amount * sp.fst(sp.ediv(self.data.swaps[params.swap_id].xtz_per_objkt, sp.mutez(1)).open_some())
            
        # calculate fees and royalties
        self.fee = self.amount * (self.data.swaps[params.swap_id].royalties + 25) / 1000
        self.royalties = self.data.swaps[params.swap_id].royalties * self.fee / (self.data.swaps[params.swap_id].royalties + 25)
        
        # send royalties to NFT creator
        sp.send(self.data.swaps[params.swap_id].creator, sp.utils.nat_to_mutez(self.royalties))
            
        # send management fees
        sp.send(self.data.manager, sp.utils.nat_to_mutez(abs(self.fee - self.royalties)))
            
        # send value to issuer
        sp.send(self.data.swaps[params.swap_id].issuer, sp.amount -  sp.utils.nat_to_mutez(self.fee))
        
        self.data.swaps[params.swap_id].objkt_amount = abs(self.data.swaps[params.swap_id].objkt_amount - params.objkt_amount)
        
        self.fa2_transfer(self.data.objkt, sp.self_address, sp.sender, self.data.swaps[params.swap_id].objkt_id, params.objkt_amount)
    
    @sp.entry_point
    def cancel_swap(self, params):
        sp.verify(sp.sender == self.data.swaps[params].issuer)
        self.fa2_transfer(self.data.objkt, sp.self_address, sp.sender, self.data.swaps[params].objkt_id, self.data.swaps[params].objkt_amount)
        del self.data.swaps[params]
        
    @sp.entry_point
    def update_manager(self, params):
        sp.verify(sp.sender == self.data.manager)
        self.data.manager = params
        
    def fa2_transfer(self, fa2, from_, to_, objkt_id, objkt_amount):
        c = sp.contract(sp.TList(sp.TRecord(from_=sp.TAddress, txs=sp.TList(sp.TRecord(amount=sp.TNat, to_=sp.TAddress, token_id=sp.TNat).layout(("to_", ("token_id", "amount")))))), fa2, entry_point='transfer').open_some()
        sp.transfer(sp.list([sp.record(from_=from_, txs=sp.list([sp.record(amount=objkt_amount, to_=to_, token_id=objkt_id)]))]), sp.mutez(0), c)