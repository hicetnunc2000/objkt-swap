import smartpy as sp

class OBJKTSwap(sp.Contract):
    def __init__(self, objkt, hdao, manager, metadata, curate):
        # TODO refactor these default variables as they can cause
        # errors when referencing the value that is returned
        self.fee = 0
        self.amount = 0
        self.royalties = 0

        self.init(
            swaps = sp.big_map(
                tkey=sp.TNat,
                tvalue=sp.TRecord(
                    issuer=sp.TAddress,
                    xtz_per_objkt=sp.TMutez,
                    objkt_id=sp.TNat,
                    objkt_amount=sp.TNat
                )
            ),
            royalties = sp.big_map(
                tkey=sp.TNat,
                tvalue=sp.TRecord(
                    issuer=sp.TAddress,
                    royalties=sp.TNat
                    # should objkt id and amount not get stored here?
                )
            ),
            swap_id = 0,
            # start objkt ids from this number
            # when upgrading contracts this must be greater
            # than the most recent objkt number
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
        sp.verify(
            (
                sp.sender == self.data.manager
            ) & ~(
                self.data.locked
            )
        )

        # what's up with adding 45 days?
        self.data.genesis = (sp.now).add_days(45)
        self.data.locked = True

    @sp.entry_point
    def update_manager(self, params):
        sp.verify(
            sp.sender == self.data.manager
        )

        self.data.manager = params

    @sp.entry_point
    def swap(self, params):
        sp.verify(params.objkt_amount > 0)
        # sp.verify(params.objkt_amount == 1)

        self.fa2_transfer(
            self.data.objkt,
            sp.sender,
            sp.to_address(sp.self),
            params.objkt_id,
            params.objkt_amount
        )

        self.data.swaps[self.data.swap_id] = sp.record(
            issuer=sp.sender,
            objkt_id=params.objkt_id,
            objkt_amount=params.objkt_amount,
            xtz_per_objkt=params.xtz_per_objkt
        )
        self.data.swap_id += 1

    @sp.entry_point
    def cancel_swap(self, params):
        sp.verify(self.data.swaps[params].issuer == sp.sender)

        self.fa2_transfer(
            self.data.objkt,
            sp.to_address(sp.self),
            sp.sender,
            self.data.swaps[params].objkt_id,
            self.data.swaps[params].objkt_amount
        )

        del self.data.swaps[params]

    @sp.entry_point
    def collect(self, params):
        sp.verify(
            (params.objkt_amount > 0) &
            # (params.objkt_amount == 1) &
            (sp.sender != self.data.swaps[params.swap_id].issuer)
        )

        sp.if (self.data.swaps[params.swap_id].xtz_per_objkt != sp.tez(0)):

            self.objkt_amount = sp.fst(
                sp.ediv(
                    sp.amount,
                    self.data.swaps[params.swap_id].xtz_per_objkt
                ).open_some()
            )

            self.amount = self.objkt_amount * sp.fst(
                sp.ediv(
                    self.data.swaps[params.swap_id].xtz_per_objkt,
                    sp.mutez(1)
                ).open_some()
            )

            sp.verify(
                (params.objkt_amount == self.objkt_amount) &
                (sp.amount == sp.utils.nat_to_mutez(self.amount)) &
                (sp.amount > sp.tez(0))
            )

            # calculate fees and royalties
            self.fee = sp.fst(
                sp.ediv(
                    sp.utils.nat_to_mutez(self.amount),
                    sp.utils.nat_to_mutez(1)).open_some()
                ) * (self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties + 25) / 1000

            self.royalties = self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties * self.fee / (self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties + 25)

            # send royalties to NFT creator
            sp.send(
                self.data.royalties[self.data.swaps[params.swap_id].objkt_id].issuer,
                sp.utils.nat_to_mutez(self.royalties)
            )

            # send management fees
            sp.send(
                self.data.manager,
                sp.utils.nat_to_mutez(
                    abs(self.fee - self.royalties)
                )
            )

            # send value to issuer
            sp.send(
                self.data.swaps[params.swap_id].issuer,
                sp.amount - sp.utils.nat_to_mutez(self.fee)
            )

            # off on test scenarios
            # sp.if (sp.now < self.data.genesis):
            #self.mint_hDAO([sp.record(to_=sp.sender, amount=self.amount / 2), sp.record(to_=self.data.swaps[params.swap_id].issuer, amount=self.amount / 2), sp.record(to_=self.data.manager, amount=abs(self.fee - self.royalties))])

        self.fa2_transfer(
            self.data.objkt,
            sp.to_address(sp.self),
            sp.sender,
            self.data.swaps[params.swap_id].objkt_id,
            params.objkt_amount
        )

        self.data.swaps[params.swap_id].objkt_amount = abs(
            self.data.swaps[params.swap_id].objkt_amount - params.objkt_amount
        )

        sp.if (self.data.swaps[params.swap_id].objkt_amount == 0):
            del self.data.swaps[params.swap_id]

    @sp.entry_point
    def mint_OBJKT(self, params):
        sp.verify(
            # at least 1 objkt
            (params.amount > 0) &
            (
                (params.royalties >= 0) &
                # max royalty
                # 250 is actually 25.0%
                (params.royalties <= 250)
            ) &
            # at most 10k objkts
            (params.amount <= 10000)
        )

        c = sp.contract(
            sp.TRecord(
                address=sp.TAddress,
                amount=sp.TNat,
                token_id=sp.TNat,
                token_info=sp.TMap(sp.TString, sp.TBytes)
            ),
            self.data.objkt,
            entry_point = "mint"
        ).open_some()

        sp.transfer(
            sp.record(
                address=params.address,
                amount=params.amount,
                token_id=self.data.objkt_id,
                token_info={ '' : params.metadata }
            ),
            sp.mutez(0),
            c
        )

        self.data.royalties[self.data.objkt_id] = sp.record(
            issuer=sp.sender,
            royalties=params.royalties
        )

        self.data.objkt_id += 1

    @sp.entry_point
    def curate(self, params):
        self.fa2_transfer(
            self.data.hdao,
            sp.sender,
            self.data.curate,
            0,
            params.hDAO_amount
        )

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
                )
            ),
            self.data.hdao,
            entry_point = "hDAO_batch"
        ).open_some()

        sp.transfer(
            params,
            sp.mutez(0),
            c
        )

    def fa2_transfer(self, fa2, from_, to_, objkt_id, objkt_amount):
        # sp.verify(objkt_amount == 1)
        sp.verify(objkt_amount > 0)

        c = sp.contract(
            sp.TList(
                sp.TRecord(
                    from_=sp.TAddress,
                    txs=sp.TList(
                        sp.TRecord(
                            amount=sp.TNat,
                            to_=sp.TAddress,
                            token_id=sp.TNat
                        ).layout(
                            (
                                "to_", (
                                    "token_id",
                                    "amount"
                                )
                            )
                        )
                    )
                )
            ),
            fa2,
            entry_point='transfer'
        ).open_some()

        sp.transfer(
            sp.list(
                [sp.record(
                    from_=from_,
                    txs=sp.list([
                        sp.record(
                            amount=objkt_amount,
                            to_=to_,
                            token_id=objkt_id
                        )
                    ])
                )]
            ),
            sp.mutez(0),
            c
        )

@sp.add_test("Class constructs with default values")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Swap Objkt Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    curator = sp.test_account("curator")
    objkt = sp.test_account("objkt123")
    hdao = sp.test_account("hdao")

    metadata = {
        "name": "something"
    }

    swap = OBJKTSwap(
        objkt.address,
        hdao.address,
        manager.address,
        metadata,
        curator.address
    )

    scenario += swap

    # default variables that get set in the contract constructor
    # TODO find out if these are the intended initial values
    scenario.verify(swap.data.swap_id == 0)
    scenario.verify(swap.data.objkt_id == 152)
    scenario.verify(swap.data.genesis == sp.timestamp(0))
    scenario.verify(swap.data.locked == False)

    # addresses are as expected
    scenario.verify(swap.data.manager == manager.address)
    scenario.verify(swap.data.hdao == hdao.address)
    scenario.verify(swap.data.curate == curator.address)
    scenario.verify(swap.data.objkt == objkt.address)

    # default values
    # TODO cannot be tested due to locally declared variables inside
    # scenario.verify(swap.royalties == 0)
    # scenario.verify(swap.fee == 0)
    # scenario.verify(swap.amount == 0)

    # metadata
    # TODO how does this work? am i passing in the metadata correctly?
    # scenario.verify(swap.data.metadata.name == 'something')

    # TODO how to test these members?
    # print(vars(swap.data.swaps))
    # print(vars(swap.data.royalties))

@sp.add_test("Test genesis entrypoint")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Genesis Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    curator = sp.test_account("curator")
    objkt = sp.test_account("objkt123")
    hdao = sp.test_account("hdao")

    metadata = {
        "name": "something"
    }

    swap = OBJKTSwap(
        objkt.address,
        hdao.address,
        manager.address,
        metadata,
        curator.address
    )

    scenario += swap

    # illegal attempts
    scenario += swap.genesis().run(sender = seller, valid = False)
    scenario += swap.genesis().run(sender = hdao, valid = False)
    scenario += swap.genesis().run(sender = curator, valid = False)
    scenario += swap.genesis().run(sender = objkt, valid = False)

    # valid attempt
    scenario += swap.genesis().run(sender = manager, valid = True)

@sp.add_test("Test update manager entrypoint")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Update Manager Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    curator = sp.test_account("curator")
    objkt = sp.test_account("objkt123")
    hdao = sp.test_account("hdao")

    metadata = {
        "name": "something"
    }

    swap = OBJKTSwap(
        objkt.address,
        hdao.address,
        manager.address,
        metadata,
        curator.address
    )

    scenario += swap

    # illegal attempts (self)
    scenario += swap.update_manager(seller.address).run(sender = seller.address, valid = False)
    scenario += swap.update_manager(hdao.address).run(sender = hdao.address, valid = False)
    scenario += swap.update_manager(curator.address).run(sender = curator.address, valid = False)
    scenario += swap.update_manager(objkt.address).run(sender = objkt.address, valid = False)

    # illegal attempts (lateral)
    scenario += swap.update_manager(seller.address).run(sender = objkt.address, valid = False)
    scenario += swap.update_manager(hdao.address).run(sender = seller.address, valid = False)
    scenario += swap.update_manager(manager.address).run(sender = curator.address, valid = False)
    scenario += swap.update_manager(curator.address).run(sender = hdao.address, valid = False)

    # situational tests

    # switch manager and confirm manager can no longer manage
    newManager = sp.test_account("newManager")

    # not valid to swap manager to curator
    scenario += swap.update_manager(curator.address).run(sender = newManager.address, valid = False)

    # valid for existing manager to change the manager
    scenario += swap.update_manager(newManager.address).run(sender = manager.address, valid = True)

    # now the new manager can change to anyone
    scenario += swap.update_manager(curator.address).run(sender = newManager.address, valid = True)

    # but old manager can no longer change manager
    scenario += swap.update_manager(seller.address).run(sender = manager.address, valid = False)

@sp.add_test("Test swap")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Swap Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    curator = sp.test_account("curator")
    objkt = sp.test_account("objkt123")
    hdao = sp.test_account("hdao")

    metadata = {
        "name": "something"
    }

    swap = OBJKTSwap(
        objkt.address,
        hdao.address,
        manager.address,
        metadata,
        curator.address
    )

    scenario += swap

    # illegal attempts (self)
    scenario += swap.update_manager(seller.address).run(sender = seller.address, valid = False)

