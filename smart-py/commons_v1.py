import smartpy as sp


# commons 1
class Multisig(sp.Contract):
    def __init__(self, manager):
        self.init(
            manager = manager,
            payout = {}
            )
    
    @sp.entry_point
    def default(self, params):
        sp.set_type(params, sp.TUnit)
        sp.for e in self.data.payout.keys():
            sp.send(e, sp.utils.nat_to_mutez(sp.fst(sp.ediv(sp.balance, sp.utils.nat_to_mutez(1)).open_some()) / 10000 * self.data.payout[e]))

    @sp.entry_point
    def hicetnunc_manager(self, params):
        sp.verify(sp.sender == self.data.manager)
        c = sp.contract(sp.TAddress, params.addr, entry_point='update_manager').open_some()
        sp.transfer(params.manager, sp.mutez(0), c)
    
    @sp.entry_point
    def self_manager(self, params):
        sp.verify(sp.sender == self.data.manager)
        self.data.manager = params
        
    @sp.entry_point
    def payout_config(self, params):
        sp.verify((sp.sender == self.data.manager))
        
        # verifies percentage distribution
        total = sp.local('total', 0)
        sp.for e in params.values():
            total.value += e
        # 6 decimals?
        sp.verify(total.value == 10000)
        
        self.data.payout = params   