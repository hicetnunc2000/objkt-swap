import smartpy as sp

class OBJKTSwap(sp.Contract):
    def __init__(self, objkt, manager, metadata):
        self.fee = 0
        self.amount = 0
        self.royalties = 0
        self.init(
            swaps = sp.big_map(tkey=sp.TNat, tvalue=sp.TRecord(issuer=sp.TAddress, xtz_per_objkt=sp.TMutez, objkt_id=sp.TNat, objkt_amount=sp.TNat)),
            royalties = sp.big_map(tkey=sp.TNat, tvalue=sp.TRecord(issuer=sp.TAddress, royalties=sp.TNat)),
            swap_id = 0,
            objkt_id = 0,
            objkt = objkt,
            manager = manager,
            metadata = metadata,
            )
    
    @sp.entry_point
    def swap(self, params):
        sp.verify(params.objkt_amount > 0)
        self.fa2_transfer(self.data.objkt, sp.sender, sp.to_address(sp.self), params.objkt_id, params.objkt_amount)
        self.data.swaps[self.data.swap_id] = sp.record(issuer=sp.sender, objkt_id=params.objkt_id, objkt_amount=params.objkt_amount, xtz_per_objkt=params.xtz_per_objkt)
        self.data.swap_id += 1
    
        
    @sp.entry_point
    def collect(self, params):
        sp.verify( (params.objkt_amount > 0) & (sp.sender != self.data.swaps[params.swap_id].issuer) )
        sp.if (self.data.swaps[params.swap_id].xtz_per_objkt != sp.tez(0)):
        
            self.objkt_amount = sp.fst(sp.ediv(sp.amount, self.data.swaps[params.swap_id].xtz_per_objkt).open_some())
            
            self.amount = self.objkt_amount * sp.fst(sp.ediv(self.data.swaps[params.swap_id].xtz_per_objkt, sp.mutez(1)).open_some())
            
            sp.verify((params.objkt_amount == self.objkt_amount) & (sp.amount == sp.mutez(self.amount)) & (sp.amount > sp.tez(0)))
            # calculate fees and royalties
            self.fee = sp.fst(sp.ediv(sp.mutez(self.amount), sp.mutez(1)).open_some()) * (self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties + 25) / 1000
            self.royalties = self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties * self.fee / (self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties + 25)
            
            # send royalties to NFT creator
            sp.send(self.data.royalties[self.data.swaps[params.swap_id].objkt_id].issuer, sp.mutez(self.royalties))
            
            # send management fees
            sp.send(self.data.manager, sp.mutez(abs(self.fee - self.royalties)))
            
            # send value to issuer
            sp.send(self.data.swaps[params.swap_id].issuer, sp.amount - sp.mutez(self.fee))
        
        self.fa2_transfer(self.data.objkt, sp.to_address(sp.self), sp.sender, self.data.swaps[params.swap_id].objkt_id, params.objkt_amount)

        self.data.swaps[params.swap_id].objkt_amount = abs(self.data.swaps[params.swap_id].objkt_amount - params.objkt_amount)
        
        sp.if (self.data.swaps[params.swap_id].objkt_amount == 0):
            del self.data.swaps[params.swap_id]
    
    @sp.entry_point
    def mint_OBJKT(self, params):
        sp.verify((params.amount > 0) & ((params.royalties >= 0) & (params.royalties <= 250)) & (sp.len(params.metadata) == 106))

        c = sp.contract(
            sp.TRecord(
            address=sp.TAddress,
            amount=sp.TNat,
            token_id=sp.TNat,
            token_info=sp.TMap(sp.TString, sp.TBytes)
            ), 
            self.data.objkt, 
            entry_point = "mint").open_some()
            
        sp.transfer(
            sp.record(
            address=params.address,
            amount=params.amount,
            token_id=self.data.objkt_id,
            token_info=params.metadata
            ), 
            sp.mutez(0), 
            c)
        
        self.data.royalties[self.data.objkt_id] = sp.record(issuer=sp.sender, royalties=params.royalties)
        self.data.objkt_id += 1
            
    def fa2_transfer(self, fa2, from_, to_, objkt_id, objkt_amount):
        c = sp.contract(sp.TList(sp.TRecord(from_=sp.TAddress, txs=sp.TList(sp.TRecord(amount=sp.TNat, to_=sp.TAddress, token_id=sp.TNat).layout(("to_", ("token_id", "amount")))))), fa2, entry_point='transfer').open_some()
        sp.transfer(sp.list([sp.record(from_=from_, txs=sp.list([sp.record(amount=objkt_amount, to_=to_, token_id=objkt_id)]))]), sp.mutez(0), c)