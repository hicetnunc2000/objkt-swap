class hDAO_Marketplace(sp.Contract):
    def __init__(self, manager, metadata, hdao, objkts):
        self.init(
            manager = manager,
            metadata = metadata,
            hdao = hdao,
            objkts = objkts,
            swaps = sp.big_map(tkey=sp.TNat, tvalue=sp.TRecord(hdao_per_objkt=sp.TNat, objkt_amount=sp.TNat, objkt_id=sp.TNat, issuer=sp.TAddress, creator=sp.TAddress, royalties=sp.TNat)),
            counter = 0,
            fee = 25
            )
    
    @sp.entry_point
    def update_manager(self, params):
        sp.verify(sp.sender == self.data.manager)
        self.data.manager = params

    @sp.entry_point
    def swap(self, params):
        self.data.swaps[self.data.counter] = sp.record(hdao_per_objkt=params.hdao_per_objkt, objkt_amount=params.objkt_amount, objkt_id=params.objkt_id, issuer=sp.sender, creator=params.creator, royalties=params.royalties)
        self.tk_transfer(self.data.objkts, sp.sender, sp.to_address(sp.self), params.objkt_id, params.objkt_amount)
        self.data.counter += 1

    @sp.entry_point
    def cancel_swap(self, params):
        sp.verify((sp.sender == self.data.swaps[params.swap_id].issuer))
        self.tk_transfer(self.data.objkts, sp.to_address(sp.self), self.data.swaps[params.swap_id].issuer, self.data.swaps[params.swap_id].objkt_id, self.data.swaps[params.swap_id].objkt_amount) 
        del self.data.swaps[params.swap_id]

    @sp.entry_point
    def collect(self, params):
        sp.verify((self.data.swaps[params.swap_id].objkt_amount > 0))
        self.tk_transfer(self.data.objkts, sp.to_address(sp.self), sp.sender, self.data.swaps[params.swap_id].objkt_id, 1)
        
        # royalties/fees
        self.fee = (self.data.swaps[params.swap_id].hdao_per_objkt * self.data.swaps[params.swap_id].royalties + self.data.fee) / 1000
        self.royalties = self.data.swaps[params.swap_id].royalties * self.fee / (self.data.swaps[params.swap_id].royalties + self.data.fee)
     
        # send royalties to NFT creator
        self.tk_transfer(self.data.hdao, sp.sender, self.data.swaps[params.swap_id].creator, 0, self.royalties)
                
        # send management fees
        self.tk_transfer(self.data.hdao, sp.sender, self.data.manager, 0, abs(self.fee - self.royalties))
                
        # send value to issuer
        self.tk_transfer(self.data.hdao, sp.sender, self.data.swaps[params.swap_id].issuer, 0, abs(self.data.swaps[params.swap_id].hdao_per_objkt - self.fee))
                
    def tk_transfer(self, kt, issuer, destination, tk_id, tk_amount):
        c = sp.contract(sp.TList(sp.TRecord(from_=sp.TAddress, txs=sp.TList(sp.TRecord(amount=sp.TNat, to_=sp.TAddress, token_id=sp.TNat).layout(("to_", ("token_id", "amount")))))), kt, entry_point='transfer').open_some()
        sp.transfer(sp.list([sp.record(from_=issuer, txs=sp.list([sp.record(amount=tk_amount, to_=destination, token_id=tk_id)]))]), sp.mutez(0), c)