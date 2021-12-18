import smartpy as sp


class OBJKTSwap(sp.Contract):
    def __init__(self, objkt, hdao, manager, metadata, curate):
        self.fee = 0
        self.amount = 0
        self.royalties = 0
        self.init(
            swaps = sp.big_map(tkey=sp.TNat, tvalue=sp.TRecord(issuer=sp.TAddress, xtz_per_objkt=sp.TMutez, objkt_id=sp.TNat, objkt_amount=sp.TNat)),
            royalties = sp.big_map(tkey=sp.TNat, tvalue=sp.TRecord(issuer=sp.TAddress, royalties=sp.TNat)),
            swap_id = 0,
            objkt_id = 152,
            objkt = objkt,
            hdao = hdao,
            manager = manager,
            metadata = metadata,
            genesis = sp.timestamp(0),
            curate = curate,
            locked = False
            )
    
    @sp.entry_point
    def genesis(self):
        sp.verify((sp.sender == self.data.manager) & ~(self.data.locked))
        self.data.genesis = (sp.now).add_days(45)
        self.data.locked = True
    
    @sp.entry_point
    def update_manager(self, params):
        sp.verify(sp.sender == self.data.manager)
        self.data.manager = params
        
    @sp.entry_point
    def swap(self, params):
        sp.verify((params.objkt_amount > 0))
        self.fa2_transfer(self.data.objkt, sp.sender, sp.to_address(sp.self), params.objkt_id, params.objkt_amount)
        self.data.swaps[self.data.swap_id] = sp.record(issuer=sp.sender, objkt_id=params.objkt_id, objkt_amount=params.objkt_amount, xtz_per_objkt=params.xtz_per_objkt)
        self.data.swap_id += 1
    
    @sp.entry_point
    def cancel_swap(self, params):
        sp.verify( (self.data.swaps[params].issuer == sp.sender) )
        self.fa2_transfer(self.data.objkt, sp.to_address(sp.self), sp.sender, self.data.swaps[params].objkt_id, self.data.swaps[params].objkt_amount)
        
        del self.data.swaps[params]
        
    @sp.entry_point
    def collect(self, params):
        sp.verify( (params.objkt_amount > 0) & (sp.sender != self.data.swaps[params.swap_id].issuer) )
        
        sp.if (self.data.swaps[params.swap_id].xtz_per_objkt != sp.tez(0)):
        
            self.objkt_amount = sp.fst(sp.ediv(sp.amount, self.data.swaps[params.swap_id].xtz_per_objkt).open_some())
            
            self.amount = self.objkt_amount * sp.fst(sp.ediv(self.data.swaps[params.swap_id].xtz_per_objkt, sp.mutez(1)).open_some())
            
            sp.verify((params.objkt_amount == self.objkt_amount) & (sp.amount == sp.utils.nat_to_mutez(self.amount)) & (sp.amount > sp.tez(0)))
            # calculate fees and royalties
            self.fee = sp.fst(sp.ediv(sp.utils.nat_to_mutez(self.amount), sp.utils.nat_to_mutez(1)).open_some()) * (self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties + 25) / 1000
            self.royalties = self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties * self.fee / (self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties + 25)
            
            # send royalties to NFT creator
            sp.send(self.data.royalties[self.data.swaps[params.swap_id].objkt_id].issuer, sp.utils.nat_to_mutez(self.royalties))
            
            # send management fees
            sp.send(self.data.manager, sp.utils.nat_to_mutez(abs(self.fee - self.royalties)))
            
            # send value to issuer
            sp.send(self.data.swaps[params.swap_id].issuer, sp.amount - sp.utils.nat_to_mutez(self.fee))
            
            # off on test scenarios
            # sp.if (sp.now < self.data.genesis):
            #self.mint_hDAO([sp.record(to_=sp.sender, amount=self.amount / 2), sp.record(to_=self.data.swaps[params.swap_id].issuer, amount=self.amount / 2), sp.record(to_=self.data.manager, amount=abs(self.fee - self.royalties))])
        
        self.fa2_transfer(self.data.objkt, sp.to_address(sp.self), sp.sender, self.data.swaps[params.swap_id].objkt_id, params.objkt_amount)

        self.data.swaps[params.swap_id].objkt_amount = abs(self.data.swaps[params.swap_id].objkt_amount - params.objkt_amount)
        
        sp.if (self.data.swaps[params.swap_id].objkt_amount == 0):
            del self.data.swaps[params.swap_id]
    
    @sp.entry_point
    def mint_OBJKT(self, params):
        sp.verify((params.amount > 0) & ((params.royalties >= 0) & (params.royalties <= 250)) & (params.amount <= 10000))
        
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
            token_info={ '' : params.metadata }
            ), 
            sp.mutez(0), 
            c)
        
        self.data.royalties[self.data.objkt_id] = sp.record(issuer=sp.sender, royalties=params.royalties)
        self.data.objkt_id += 1
    
    @sp.entry_point
    def curate(self, params):
        self.fa2_transfer(self.data.hdao, sp.sender, self.data.curate, 0, params.hDAO_amount)
        
        c = sp.contract(
            sp.TRecord(
                hDAO_amount = sp.TNat,
                objkt_id = sp.TNat,
                issuer = sp.TAddress
                ),
                self.data.curate,
                entry_point = 'curate'
            ).open_some()
        
        sp.transfer(
            sp.record(
                hDAO_amount = params.hDAO_amount,
                objkt_id = params.objkt_id,
                issuer = self.data.royalties[params.objkt_id].issuer
                ),
                sp.mutez(0),
                c
            )
            
    def mint_hDAO(self, params):
        
        c = sp.contract(
            sp.TList(
            sp.TRecord(
            to_=sp.TAddress,
            amount=sp.TNat
            )), 
            self.data.hdao, 
            entry_point = "hDAO_batch").open_some()
            
        sp.transfer(
            params, 
            sp.mutez(0), 
            c)
        
    def fa2_transfer(self, fa2, from_, to_, objkt_id, objkt_amount):
        c = sp.contract(sp.TList(sp.TRecord(from_=sp.TAddress, txs=sp.TList(sp.TRecord(amount=sp.TNat, to_=sp.TAddress, token_id=sp.TNat).layout(("to_", ("token_id", "amount")))))), fa2, entry_point='transfer').open_some()
        sp.transfer(sp.list([sp.record(from_=from_, txs=sp.list([sp.record(amount=objkt_amount, to_=to_, token_id=objkt_id)]))]), sp.mutez(0), c)
