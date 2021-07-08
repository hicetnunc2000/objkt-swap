import smartpy as sp
import os

OBJKTSwap = sp.io.import_script_from_url(f"file://{os.getcwd()}/objkt_swap.py").OBJKTSwap

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

    creator = sp.test_account("creator")
    metadata = sp.record(
        name = "test",
        description = "test",
        tags = [
            'test'
        ],
        symbol = 'OBJKT',
        artifactUri = "ipfs://test",
        displayUri = "ipfs://test",
        thumbnailUri = "ipfs://test",
        creators = [
            creator.address
        ],
        formats = [
            {
                "uri":"ipfs://test",
                "mimeType":"image/png"
            }
        ],
        decimals = 0,
        isBooleanAmount = False,
        shouldPreferSymbol = False
    )

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

    creator = sp.test_account("creator")
    metadata = sp.record(
        name = "test",
        description = "test",
        tags = [
            'test'
        ],
        symbol = 'OBJKT',
        artifactUri = "ipfs://test",
        displayUri = "ipfs://test",
        thumbnailUri = "ipfs://test",
        creators = [
            creator.address
        ],
        formats = [
            {
                "uri":"ipfs://test",
                "mimeType":"image/png"
            }
        ],
        decimals = 0,
        isBooleanAmount = False,
        shouldPreferSymbol = False
    )

    swap = OBJKTSwap(
        objkt.address,
        hdao.address,
        manager.address,
        metadata,
        curator.address
    )

    scenario += swap

    # initial state
    scenario.verify(swap.data.locked == False)
    scenario.verify(swap.data.genesis == sp.timestamp(0))

    # illegal attempts
    scenario += swap.genesis().run(sender = seller, valid = False)
    scenario += swap.genesis().run(sender = hdao, valid = False)
    scenario += swap.genesis().run(sender = curator, valid = False)
    scenario += swap.genesis().run(sender = objkt, valid = False)

    # no change
    scenario.verify(swap.data.locked == False)
    scenario.verify(swap.data.genesis == sp.timestamp(0))

    # valid attempt
    scenario += swap.genesis().run(sender = manager, valid = True)

    # updated and locked
    scenario.verify(swap.data.locked == True)
    scenario.verify(swap.data.genesis == sp.timestamp(0).add_days(45))

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

    creator = sp.test_account("creator")
    metadata = sp.record(
        name = "test",
        description = "test",
        tags = [
            'test'
        ],
        symbol = 'OBJKT',
        artifactUri = "ipfs://test",
        displayUri = "ipfs://test",
        thumbnailUri = "ipfs://test",
        creators = [
            creator.address
        ],
        formats = [
            {
                "uri":"ipfs://test",
                "mimeType":"image/png"
            }
        ],
        decimals = 0,
        isBooleanAmount = False,
        shouldPreferSymbol = False
    )

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

    creator = sp.test_account("creator")
    metadata = sp.record(
        name = "test",
        description = "test",
        tags = [
            'test'
        ],
        symbol = 'OBJKT',
        artifactUri = "ipfs://test",
        displayUri = "ipfs://test",
        thumbnailUri = "ipfs://test",
        creators = [
            creator.address
        ],
        formats = [
            {
                "uri":"ipfs://test",
                "mimeType":"image/png"
            }
        ],
        decimals = 0,
        isBooleanAmount = False,
        shouldPreferSymbol = False
    )

    swap = OBJKTSwap(
        objkt.address,
        hdao.address,
        manager.address,
        metadata,
        curator.address
    )

    scenario += swap

    # no swaps or objkts yet
    scenario.verify(swap.data.swap_id == 0)
    scenario.verify(swap.data.objkt_id == 152)
    scenario.verify(swap.data.swaps.contains(0) == False)

    # swap with objkt id above max must fail
    scenario += swap.swap(
        objkt_id = 153,
        objkt_amount = 2,
        xtz_per_objkt = sp.utils.nat_to_mutez(1)
    ).run(
        sender = seller.address,
        valid = False
    )

    # nothing changed because the swap failed as no swaps were created
    scenario.verify(swap.data.swap_id == 0)
    scenario.verify(swap.data.objkt_id == 152)
    scenario.verify(swap.data.swaps.contains(0) == False)

    # add an 1/1 objkt to the contract
    # the address and the sender are both the creator
    scenario += swap.mint_OBJKT(
        address = creator.address,
        amount = 1,
        royalties = 200,
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = creator.address,
        valid = True
    )

    # the mint was successful but still no swap
    scenario.verify(swap.data.objkt_id == 153)
    scenario.verify(swap.data.swap_id == 0)
    scenario.verify(swap.data.swaps.contains(0) == False)

    # try swap more objkts than exist must fail
    # TODO this should fail and currently does not
    # scenario += swap.swap(
    #     objkt_id = 153,
    #     objkt_amount = 2,
    #     xtz_per_objkt = sp.utils.nat_to_mutez(1)
    # ).run(
    #     sender = seller.address,
    #     valid = False
    # )

    # swap id should not have incremented
    # scenario.verify(swap.data.swaps.contains(0) == False)

    # swap with new objkt id must pass
    scenario += swap.swap(
        objkt_id = 153,
        objkt_amount = 1,
        xtz_per_objkt = sp.utils.nat_to_mutez(1)
    ).run(
        sender = seller.address,
        valid = True
    )

    # one swap was added
    scenario.verify(swap.data.swaps.contains(0) == True)
    scenario.verify(swap.data.swaps.contains(1) == False)
    scenario.verify(swap.data.swap_id == 1)
    scenario.verify(swap.data.swaps.get(0).objkt_id == 153)

    # swap should now fail because there is only 1 objkt available
    # TODO this currently passes and a swap gets added breaking all
    # of the tests that have been commented out below
    #
    # tests below may be making incorrect assumptions, do not assume they
    # are correct because i haven't been able to continue due to this
    # first bug
    #
    # scenario += swap.swap(
        # objkt_id = 153,
        # objkt_amount = 1,
        # xtz_per_objkt = sp.utils.nat_to_mutez(2)
    # ).run(sender = seller.address, valid = False)
    #
    # # swap should not have been added because the swap should not
    # exist anymore but it gets added
    #
    # scenario.verify(swap.data.swap_id == 1)
    # scenario.verify(swap.data.swaps.contains(1) == False)
    #
    # # add a multiple edition from the same creator
    # # the address and the sender are both the creator
    # scenario += swap.mint_OBJKT(
    #     address = creator.address,
    #     amount = 3,
    #     royalties = 250,
    #     metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    # ).run(
    #     sender = creator.address,
    #     valid = True
    # )
    #
    # scenario.verify(swap.data.objkt_id == 154)
    # scenario.verify(swap.data.swap_id == 1)
    # scenario.verify(swap.data.swaps.contains(1) == False)
    #
    # # claim multiple editions
    # scenario += swap.swap(
    #     objkt_id = 154,
    #     objkt_amount = 2,
    #     xtz_per_objkt = sp.utils.nat_to_mutez(1)
    # ).run(sender = seller.address, valid = False)
    #
    # # there should be 2 more swaps
    # scenario.verify(swap.data.objkt_id == 154)
    # scenario.verify(swap.data.swap_id == 3)
    # scenario.verify(swap.data.swaps.contains(3) == True)
    # scenario.verify(swap.data.swaps.contains(4) == False)
    #
    # # zero swaps for the last one should fail
    # scenario += swap.swap(
    #     objkt_id = 154,
    #     objkt_amount = 0,
    #     xtz_per_objkt = sp.utils.nat_to_mutez(1)
    # ).run(sender = seller.address, valid = False)
    #
    # # one swap should pass
    # # TODO add and test validation that sender is owner of objkt
    # scenario += swap.swap(
    #     objkt_id = 123456,
    #     objkt_amount = 1,
    #     xtz_per_objkt = sp.utils.nat_to_mutez(1)
    # ).run(sender = seller.address, valid = True)
    #
    # # one more
    # scenario.verify(swap.data.objkt_id == 155)
    # scenario.verify(swap.data.swap_id == 4)
    # scenario.verify(swap.data.swaps.contains(4) == True)
    # scenario.verify(swap.data.swaps.contains(5) == False)

    # TODO test the couunter tally

@sp.add_test("Test cancel swap")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Cancel Swap Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    curator = sp.test_account("curator")
    objkt = sp.test_account("objkt123")
    hdao = sp.test_account("hdao")

    creator = sp.test_account("creator")

    # TODO how do i turn this metadata into the expected binary object?
    metadata = sp.record(
        name = "test",
        description = "test",
        tags = [
            'test'
        ],
        symbol = 'OBJKT',
        artifactUri = "ipfs://test",
        displayUri = "ipfs://test",
        thumbnailUri = "ipfs://test",
        creators = [
            creator.address
        ],
        formats = [
            {
                "uri":"ipfs://test",
                "mimeType":"image/png"
            }
        ],
        decimals = 0,
        isBooleanAmount = False,
        shouldPreferSymbol = False
    )

    swap = OBJKTSwap(
        objkt.address,
        hdao.address,
        manager.address,
        metadata,
        curator.address
    )

    scenario += swap

    # add an 1/1 objkt to the contract
    # the address and the sender are both the creator
    scenario += swap.mint_OBJKT(
        address = creator.address,
        amount = 1,
        royalties = 200,
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = creator.address,
        valid = True
    )

    # add a swap
    scenario += swap.swap(
        objkt_id = 153,
        objkt_amount = 1,
        xtz_per_objkt = sp.utils.nat_to_mutez(1)
    ).run(
        sender = seller.address,
        valid = True
    )

    scenario.verify(swap.data.swap_id == 1)
    scenario.verify(swap.data.swaps.contains(0) == True)

    # cancel the most recent one
    # the index starts at 0 so is 1 less than the swap id at this point
    scenario += swap.cancel_swap(0).run(
        sender = seller.address,
        valid = True
    )

    # this remain incremented
    scenario.verify(swap.data.swap_id == 1)

    # but the swap no longer exists
    scenario.verify(swap.data.swaps.contains(0) == False)

    # try cancel nonexistent
    scenario += swap.cancel_swap(1535).run(
        sender = seller.address,
        valid = False
    )

    # make another swap now that there's a cancellation
    scenario += swap.swap(
        objkt_id = 153,
        objkt_amount = 1,
        xtz_per_objkt = sp.utils.nat_to_mutez(1)
    ).run(
        sender = seller.address,
        valid = True
    )

    # incremented
    scenario.verify(swap.data.swap_id == 2)

    # but only 1 swap that did not go into the same position the
    # cancelled one was in originally
    scenario.verify(swap.data.swaps.contains(0) == False)
    scenario.verify(swap.data.swaps.contains(1) == True)
    scenario.verify(swap.data.swaps.contains(2) == False)

    # try to cancel someone elses swap
    scenario += swap.cancel_swap(1).run(
        sender = manager.address,
        valid = False
    )

    # swap still exists and was not cancelled
    scenario.verify(swap.data.swaps.contains(1) == True)

    # TODO multiple edition tests

@sp.add_test("Test collect swap")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Collect Swap Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    curator = sp.test_account("curator")
    objkt = sp.test_account("objkt123")
    hdao = sp.test_account("hdao")

    creator = sp.test_account("creator")

    # TODO how do i turn this metadata into the expected binary object?
    metadata = sp.record(
        name = "test",
        description = "test",
        tags = [
            'test'
        ],
        symbol = 'OBJKT',
        artifactUri = "ipfs://test",
        displayUri = "ipfs://test",
        thumbnailUri = "ipfs://test",
        creators = [
            creator.address
        ],
        formats = [
            {
                "uri":"ipfs://test",
                "mimeType":"image/png"
            }
        ],
        decimals = 0,
        isBooleanAmount = False,
        shouldPreferSymbol = False
    )

    swap = OBJKTSwap(
        objkt.address,
        hdao.address,
        manager.address,
        metadata,
        curator.address
    )

    scenario += swap

    # add an 1/1 objkt to the contract
    # the address and the sender are both the creator
    scenario += swap.mint_OBJKT(
        address = creator.address,
        amount = 1,
        royalties = 200,
        # how to turn json into this?
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = creator.address,
        valid = True
    )

    scenario.verify(swap.data.swap_id == 0)
    scenario.verify(swap.data.swaps.contains(0) == False)

    # add a swap
    scenario += swap.swap(
        objkt_id = 152,
        objkt_amount = 1,
        xtz_per_objkt = sp.utils.nat_to_mutez(1)
    ).run(
        sender = seller.address,
        valid = True
    )

    scenario.verify(swap.data.swap_id == 1)
    scenario.verify(swap.data.swaps.contains(0) == True)
    scenario.verify(swap.data.swaps.contains(1) == False)

    # try to collect own swap and fail
    scenario += swap.collect(
        objkt_amount = 1,
        swap_id = 0
    ).run(
        sender = seller.address,
        amount = sp.mutez(1),
        valid = False
    )

    # still exists
    scenario.verify(swap.data.swap_id == 1)
    scenario.verify(swap.data.swaps.contains(0) == True)
    scenario.verify(swap.data.swaps.contains(1) == False)

    # someone else try to swap the objkt
    # TODO this objkt should know this sender does not have this objkt
    # scenario += swap.swap(
    #     objkt_id = 152,
    #     objkt_amount = 1,
    #     xtz_per_objkt = sp.utils.nat_to_mutez(1)
    # ).run(
    #     sender = manager.address,
    #     valid = False
    # )
    #
    # scenario.verify(swap.data.swap_id == 1)
    # scenario.verify(swap.data.swaps.contains(0) == True)
    # scenario.verify(swap.data.swaps.contains(1) == False)

    # someone else collect
    buyer = sp.test_account("buyer")

    # this should pass
    scenario += swap.collect(
        objkt_amount = 1,
        swap_id = 0
    ).run(
        sender = buyer.address,
        amount = sp.mutez(1),
        valid = True
    )

    scenario.verify(swap.data.swap_id == 1)
    scenario.verify(swap.data.swaps.contains(0) == False)
    scenario.verify(swap.data.swaps.contains(1) == False)

    # but only once because it's been collected
    scenario += swap.collect(
        objkt_amount = 1,
        swap_id = 0
    ).run(
        sender = buyer.address,
        amount = sp.mutez(1),
        valid = False
    )

    # someone else try to swap the new owners objkt
    # TODO this should fail
    # scenario += swap.swap(
    #     objkt_id = 152,
    #     objkt_amount = 1,
    #     xtz_per_objkt = sp.utils.nat_to_mutez(1)
    # ).run(
    #     sender = manager.address,
    #     valid = False
    # )
    # scenario.verify(swap.data.swap_id == 1)
    # scenario.verify(swap.data.swaps.contains(0) == False)
    # scenario.verify(swap.data.swaps.contains(1) == False)

    # try swap 0 and fail
    scenario += swap.swap(
        objkt_id = 152,
        objkt_amount = 0,
        xtz_per_objkt = sp.utils.nat_to_mutez(1)
    ).run(
        sender = buyer.address,
        valid = False
    )

    # new owner makes a swap
    scenario += swap.swap(
        objkt_id = 152,
        objkt_amount = 1,
        xtz_per_objkt = sp.utils.nat_to_mutez(1)
    ).run(
        sender = buyer.address,
        valid = True
    )

    scenario.verify(swap.data.swap_id == 2)
    scenario.verify(swap.data.swaps.contains(0) == False)
    scenario.verify(swap.data.swaps.contains(1) == True)
    scenario.verify(swap.data.swaps.contains(2) == False)

    # TODO multiple edition tests

@sp.add_test("Test mint")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Mint Objkt Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    curator = sp.test_account("curator")
    objkt = sp.test_account("objkt123")
    hdao = sp.test_account("hdao")

    creator = sp.test_account("creator")

    # TODO how do i turn this metadata into the expected binary object?
    metadata = sp.record(
        name = "test",
        description = "test",
        tags = [
            'test'
        ],
        symbol = 'OBJKT',
        artifactUri = "ipfs://test",
        displayUri = "ipfs://test",
        thumbnailUri = "ipfs://test",
        creators = [
            creator.address
        ],
        formats = [
            {
                "uri":"ipfs://test",
                "mimeType":"image/png"
            }
        ],
        decimals = 0,
        isBooleanAmount = False,
        shouldPreferSymbol = False
    )

    swap = OBJKTSwap(
        objkt.address,
        hdao.address,
        manager.address,
        metadata,
        curator.address
    )

    scenario += swap

    scenario.verify(swap.data.objkt_id == 152)

    # try add 0 copies and fail
    # the address and the sender are both the creator
    scenario += swap.mint_OBJKT(
        address = creator.address,
        amount = 0,
        royalties = 200,
        # how to turn json into this?
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = creator.address,
        valid = False
    )

    # hasn't changed
    scenario.verify(swap.data.objkt_id == 152)

    # try add more than 10k
    scenario += swap.mint_OBJKT(
        address = creator.address,
        amount = 1000000,
        royalties = 200,
        # how to turn json into this?
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = creator.address,
        valid = False
    )

    # hasn't changed
    scenario.verify(swap.data.objkt_id == 152)

    # no royalties are tracked yet
    scenario.verify(swap.data.royalties.contains(152) == False)

    # add an 1/1 objkt
    scenario += swap.mint_OBJKT(
        address = creator.address,
        amount = 1,
        royalties = 200,
        # how to turn json into this?
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = creator.address,
        valid = True
    )

    # royalty settings has been recorded for the new objkt
    scenario.verify(swap.data.royalties.contains(152) == True)
    scenario.verify(swap.data.royalties.get(152).issuer == creator.address)
    scenario.verify(swap.data.royalties.get(152).royalties == 200)

    # incrementer has gone up
    scenario.verify(swap.data.objkt_id == 153)
    scenario.verify(swap.data.royalties.contains(153) == False)

    # still no swap
    scenario.verify(swap.data.swap_id == 0)
    scenario.verify(swap.data.swaps.contains(0) == False)

    # try to mint an objkt on behalf of someone else and fail
    scenario += swap.mint_OBJKT(
        address = creator.address,
        amount = 1,
        royalties = 200,
        # how to turn json into this?
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = manager.address,
        valid = False
    )

    # no change
    scenario.verify(swap.data.swaps.contains(0) == False)
    scenario.verify(swap.data.objkt_id == 153)
    scenario.verify(swap.data.royalties.contains(153) == False)

    # try to mint an objkt with too many royalties
    scenario += swap.mint_OBJKT(
        address = creator.address,
        amount = 2,
        royalties = 300,
        # how to turn json into this?
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = creator.address,
        valid = False
    )

    # no change
    scenario.verify(swap.data.objkt_id == 153)
    scenario.verify(swap.data.royalties.contains(153) == False)

    # try to mint without metadata and fail
    #
    # TODO null metadata should fail but passes currently
    #
    # scenario += swap.mint_OBJKT(
    #     address = creator.address,
    #     amount = 1,
    #     royalties = 200,
    #     # how to turn json into this?
    #     metadata = sp.bytes('0x00')
    # ).run(
    #     sender = creator.address,
    #     valid = False
    # )
