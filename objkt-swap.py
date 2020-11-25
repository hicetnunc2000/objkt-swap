
# @hicetnunc2000 objkt-swap

import smartpy as sp

FA2 = sp.import_template("FA2.py")

        
class hicetnuncNFTs(sp.Contract):
    def __init__(self, fa2):
        self.init(
            fa2 = fa2,
            nft_counter = sp.nat(1)
            )
        
    @sp.entry_point
    def mint_hicetnuncNFT(self, params):
        
        c = sp.contract(
            sp.TRecord(
            address=sp.TAddress,
            amount=sp.TNat,
            token_id=sp.TNat,
            symbol=sp.TString
            ), 
            self.data.fa2, 
            entry_point = "mint").open_some()
            
        sp.transfer(
            sp.record(
            address=params.address,
            amount=params.amount,
            token_id=self.data.nft_counter,
            symbol=params.ipfs
            ), 
            sp.mutez(0), 
            c)
        
        self.data.nft_counter += 1


class Buy(sp.Contract):
    def __init__(self, fa2, tk_id, roll_price, timelock):
        self.init(
            fa2=fa2,
            tk_id=tk_id,
            roll_price=sp.tez(roll_price),
            res = 0,
            timelock = timelock,
            div = 0
            )
    
    @sp.entry_point
    def deposit(self, params):
        pass
    
    @sp.entry_point
    def sell(self, params):
        
        div = sp.local('div', sp.ediv(sp.amount, self.data.roll_price))
        self.data.div = sp.fst(div.value.open_some())
        
        c = sp.contract(
            sp.TList(
                sp.TRecord(
                from_=sp.TAddress, txs=sp.TList(sp.TRecord(amount=sp.TNat, to_=sp.TAddress, token_id=sp.TNat).layout(
                ("to_", ("token_id", "amount"))
            )))), self.data.fa2, entry_point='transfer').open_some()
        sp.transfer(sp.list([sp.record(from_=sp.sender, txs=sp.list([sp.record(amount=params.amount, to_=sp.to_address(sp.self), token_id=self.data.tk_id)]))]), sp.mutez(0), c)
        
    @sp.entry_point
    def verify_balance(self, params):
        
        c = sp.contract(sp.TRecord(callback = sp.TContract(sp.TList(sp.TRecord(request = sp.TRecord(
            owner = sp.TAddress,
            token_id = sp.TNat).layout(("owner", "token_id")), balance = sp.TNat).layout(("request", "balance")))), requests = sp.TList(sp.TRecord(owner = sp.TAddress, token_id = sp.TNat).layout(("owner", "token_id")))).layout(("requests", "callback")), self.data.fa2, entry_point='balance_of').open_some()


        sp.transfer(sp.record(callback = sp.contract(sp.TList(sp.TRecord(request = sp.TRecord(
            owner = sp.TAddress,
            token_id = sp.TNat).layout(("owner", "token_id")), balance = sp.TNat).layout(("request", "balance"))),
                    sp.to_address(sp.self),
                    entry_point = "return_balance").open_some(), requests = [sp.record(owner=sp.to_address(sp.self), token_id=self.data.tk_id)]), sp.mutez(0), c)
    
    # fa2 response with self.kt tk_id balance
    @sp.entry_point
    def return_balance(self, params):
        sp.verify(sp.sender == self.data.fa2)
        sp.set_type(params, (sp.TList(sp.TRecord(request = sp.TRecord(
            owner = sp.TAddress,
            token_id = sp.TNat).layout(("owner", "token_id")), balance = sp.TNat).layout(("request", "balance")))))
            
        sp.for e in params:
            self.data.res = e.balance
            

class Sell(sp.Contract):
    def __init__(self, protocol, issuer, tk_id, price_per_tk, tk_amount, timelock):
        self.init(
            #contracts whitelisting inter sc verification?
            protocol=protocol,
            issuer=issuer,
            tk_id=tk_id,
            price_per_tk=sp.tez(price_per_tk),
            tk_amount=abs(tk_amount),
            timelock =sp.timestamp(timelock)
            )
    
    @sp.entry_point
    def buy(self, params):
        sp.verify(sp.amount >= self.data.price_per_tk)
        sp.verify(sp.amount >= sp.tez(1))
        #sp.verify(sp.now < self.data.timelock)
        
        self.tk_transfer(sp.sender, sp.fst(sp.ediv(sp.split_tokens(sp.amount, 1, sp.fst(sp.ediv(self.data.price_per_tk, sp.tez(1)).open_some())),sp.tez(1)).open_some()))
        
        sp.send(self.data.issuer, sp.amount, message = None)
        
        
        
    def tk_transfer(self, destination, tk_amount):
        c = sp.contract(sp.TRecord(kreuz=sp.TBool, destination=sp.TAddress, tk_amount=sp.TNat), self.data.protocol, entry_point='swap').open_some()
        sp.transfer(sp.record(kreuz=True, destination=destination, tk_amount=tk_amount), sp.mutez(0), c)
        
            
class ObjktivSwap(sp.Contract):
    def __init__(self, fa2, oracle):
        self.sell = Sell(sp.address('tz1'), sp.address('tz1'), 0, 0, 0, 0)
        self.fee = sp.mutez(0)
        self.kt = sp.address('tz1')
        self.init(
            fa2 = fa2,
            oracle = oracle,
            sell_orders = sp.big_map(tkey=sp.TAddress, tvalue=sp.TRecord(issuer=sp.TAddress, timelock=sp.TTimestamp, tk_id=sp.TNat, tk_amount=sp.TNat, fee=sp.TMutez)),
            white_list = sp.big_map(tkey=sp.TAddress, tvalue=sp.TBool)
            )

    @sp.entry_point
    def originate_sell_order(self, params):
        sp.set_type(params, sp.TRecord(tk_id=sp.TNat, price_per_tk=sp.TNat, tk_amount=sp.TNat, timeframe=sp.TOption(sp.TInt)))
        self.fee = sp.split_tokens(sp.mutez(10000), sp.as_nat(params.timeframe.open_some()), 1)
        
        sp.verify((sp.amount >= self.fee))
        
        self.kt = sp.some(
            sp.create_contract(
                storage = sp.record(
                    protocol = sp.to_address(sp.self),
                    issuer = sp.sender,
                    tk_id = params.tk_id,
                    price_per_tk = sp.mutez(params.price_per_tk),
                    tk_amount = params.tk_amount,
                    timelock = (sp.now).add_days(params.timeframe.open_some())
                    ), contract = self.sell)).open_some()
                    
        self.data.sell_orders[self.kt] = sp.record(issuer=sp.sender, timelock=(sp.now).add_days(params.timeframe.open_some()), tk_id=params.tk_id, tk_amount=params.tk_amount, fee=self.fee)
        
        #self.exe_operator(params.fa2, sp.sender, sp.self, params.tk_id, params.tk_amount)
    
    def exe_operator(self, issuer, destination, tk_id, tk_amount):
        
        c = sp.contract(sp.TList(sp.TRecord(from_=sp.TAddress, txs=sp.TList(sp.TRecord(amount=sp.TNat, to_=sp.TAddress, token_id=sp.TNat).layout(("to_", ("token_id", "amount")))))), self.data.fa2, entry_point='transfer').open_some()
        sp.transfer(sp.list([sp.record(from_=issuer, txs=sp.list([sp.record(amount=tk_amount, to_=destination, token_id=tk_id)]))]), sp.mutez(0), c)
        
    @sp.entry_point
    def swap(self, params):
        sp.if ( params.kreuz == True ):
            sp.set_type(params, sp.TRecord(kreuz=sp.TBool, destination=sp.TAddress, tk_amount=sp.TNat))
            sp.verify((sp.now < self.data.sell_orders[sp.sender].timelock) & (params.tk_amount <= self.data.sell_orders[sp.sender].tk_amount) & (abs(self.data.sell_orders[sp.sender].tk_amount - params.tk_amount) > 0))
            self.exe_operator(self.data.sell_orders[sp.sender].issuer, params.destination, self.data.sell_orders[sp.sender].tk_id, params.tk_amount)
            self.data.sell_orders[sp.sender].tk_amount = abs(self.data.sell_orders[sp.sender].tk_amount - params.tk_amount)
        


if "templates" not in __name__:
    @sp.add_test(name = "hicetnuncNFTs")
    def test():
        scenario = sp.test_scenario()

        user = sp.test_account('3')
        user2= sp.test_account('10')
        admin = sp.test_account('4')
        
        fa2 = FA2.FA2(FA2.environment_config(), admin.address)
        hNFTs = hicetnuncNFTs(fa2.address)
        obj = ObjktivSwap(fa2.address, admin.address)
        
        scenario = sp.test_scenario()
        scenario += obj
        scenario += fa2
        
        scenario += fa2.set_administrator(hNFTs.address).run(sender=admin)

        scenario.h1("objkt-swap")
        
        scenario.show([user, admin])

        scenario += hNFTs
        
        scenario.h1("mint objkt#1")
        
        scenario += hNFTs.mint_hicetnuncNFT(address=user2.address, ipfs='QmcBXzLWiBGpQtiZRtK4D486xkEpdCXc4QDoX3WMGARmG1', amount=40).run(sender=user2)
        
        scenario.h1('allow objkt as operator')
        scenario += fa2.update_operators([
                sp.variant("add_operator", fa2.operator_param.make(
                    owner = user2.address,
                    operator = obj.address,
                    token_id = 1))]).run(sender=user2)
        
        scenario.h1('sell order objkt')
        scenario += obj.originate_sell_order(tk_id=1, price_per_tk=20, tk_amount=10, timeframe=sp.some(2)).run(sender=user2, amount=sp.mutez(1000000))

        # buying scenario not supported on smartpy ide? but united tested on delphinet

        