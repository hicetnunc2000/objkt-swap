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
        # must be at least one edition
        sp.verify(params.objkt_amount > 0)
        # no more than 10k
        sp.verify(params.objkt_amount <= 10000)
        # the objkt id must be at least 1
        # TODO make this at least the starting number (152 atm)
        sp.verify(params.objkt_id > 0)
        # the objkt number should not be beyond the max number
        sp.verify(params.objkt_id <= self.data.objkt_id)

        # get the objkt
        # TODO how to get the details of the objkt???
        # this is where i want to get the details of the objkt
        # by id from its contract but i don't know how to do this
        #
        # my last attempt was something like this:
        #
        # c = sp.record(
        #     token_id = params.objkt_id
        # )
        #
        # sp.result(c.token_id)
        # sp.verify(c.token_id == params.objkt_id)
        # print(c.amount)
        # sp.verify(c.amount > 0)

        # sp.verify(params.objkt_id == c.token_id)
        # sp.verify(params.objkt_amount <= c.amount)

        sp.verify(params.objkt_id <= self.data.objkt_id)

        # the swap must carry a value of at least 0
        sp.verify(params.xtz_per_objkt >= sp.utils.nat_to_mutez(0))

        # TODO verify sender has the objkt and the number of editions they
        # have is no more than their max number

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
            # (params.objkt_amount > 0) &
            (params.objkt_amount == 1) &
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
                (
                    params.objkt_amount == self.objkt_amount
                ) &
                (
                    sp.amount == sp.utils.nat_to_mutez(self.amount)
                ) &
                (
                    sp.amount > sp.tez(0)
                )
            )

            # calculate fees and royalties
            self.fee = sp.fst(
                sp.ediv(
                    sp.utils.nat_to_mutez(self.amount),
                    sp.utils.nat_to_mutez(1)).open_some()
                ) * (
                    self.data.royalties[self.data.swaps[params.swap_id].objkt_id].royalties + 25
                ) / 1000

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
            # no more than 10l
            (params.amount <= 10000) &
            (
                (params.royalties >= 0) &
                # max royalty
                # 250 is actually 25.0%
                (params.royalties <= 250)
            ) &
            (sp.sender == params.address)
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

        # TODO if the sender 
        self.data.royalties[self.data.objkt_id] = sp.record(
            issuer=sp.sender,
            royalties=params.royalties
        )

        self.data.objkt_id += 1

    # TODO i want an entrypoint i can send an objkt id to and get back
    # data about the objkt like max editions, issuer and royalty info
    # @sp.entry_point
    # def details(self, params):
    #     print('details')
    #
    #     c = sp.contract(
    #         sp.TInt,
    #         params.objkt_id,
    #     ).open_some()
    #
    #     print(c.token_id)
    #
    #     print('-----------')

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
