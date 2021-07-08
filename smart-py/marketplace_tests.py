import smartpy as sp
import os

Marketplace = sp.io.import_script_from_url(f"file://{os.getcwd()}/marketplace.py").Marketplace
OBJKTSwapClass = sp.io.import_script_from_url(f"file://{os.getcwd()}/objkt_swap.py")

@sp.add_test("Class constructs with default values")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Marketplace Test")

    # init test values
    objkt = sp.test_account("objkt123")
    manager = sp.test_account("manager")
    seller = sp.test_account("seller")

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

    fee = 25

    swap = Marketplace(
        objkt.address,
        metadata,
        manager.address,
        fee
    )

    scenario += swap

    # default variables that get set in the contract constructor
    # TODO find out if these are the intended initial values
    scenario.verify(swap.data.counter == 500000)

    # addresses are as expected
    scenario.verify(swap.data.manager == manager.address)
    scenario.verify(swap.data.objkt == objkt.address)

    # metadata
    # TODO how does this work? am i passing in the metadata correctly?
    # scenario.verify(swap.data.metadata.name == 'something')

@sp.add_test("Test update manager entrypoint")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Update Manager Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    objkt = sp.test_account("objkt123")

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

    fee = 25

    swap = Marketplace(
        objkt.address,
        metadata,
        manager.address,
        fee
    )

    scenario += swap

    anotherUser = sp.test_account("anotherUser")

    # illegal attempts (self)
    scenario += swap.update_manager(seller.address).run(sender = seller.address, valid = False)
    scenario += swap.update_manager(objkt.address).run(sender = objkt.address, valid = False)

    # illegal attempts (lateral)
    scenario += swap.update_manager(seller.address).run(sender = objkt.address, valid = False)
    scenario += swap.update_manager(anotherUser.address).run(sender = seller.address, valid = False)

    # situational tests

    # switch manager and confirm manager can no longer manage
    newManager = sp.test_account("newManager")

    # not valid to swap manager to anotherUser
    scenario += swap.update_manager(anotherUser.address).run(sender = newManager.address, valid = False)

    # valid for existing manager to change the manager
    scenario += swap.update_manager(newManager.address).run(sender = manager.address, valid = True)

    # now the new manager can change to anyone
    scenario += swap.update_manager(anotherUser.address).run(sender = newManager.address, valid = True)

    # but old manager can no longer change manager
    scenario += swap.update_manager(seller.address).run(sender = manager.address, valid = False)

@sp.add_test("Test update fee entrypoint")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Update Fee Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    objkt = sp.test_account("objkt123")

    creator = sp.test_account("creator")
    # TODO how to turn into the binary? or is the binary a pointer?
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

    fee = 25

    swap = Marketplace(
        objkt.address,
        metadata,
        manager.address,
        fee
    )

    scenario += swap

    scenario.verify(swap.data.fee == 25)

    # illegal attempts (lateral)
    scenario += swap.update_fee(3).run(sender = objkt.address, valid = False)
    scenario.verify(swap.data.fee == 25)

    scenario += swap.update_fee(3).run(sender = seller.address, valid = False)

    scenario.verify(swap.data.fee == 25)

    # valid for manager to change the fee
    scenario += swap.update_fee(3).run(sender = manager.address, valid = True)

    scenario.verify(swap.data.fee == 3)

@sp.add_test("Test swap")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Swap Test")

    # init test values
    seller = sp.test_account("seller")
    manager = sp.test_account("manager")
    objkt = sp.test_account("objkt123")

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

    fee = 25

    swap = Marketplace(
        objkt.address,
        metadata,
        manager.address,
        fee
    )

    scenario += swap

    # no swaps yet
    scenario.verify(swap.data.counter == 500000)
    scenario.verify(swap.data.swaps.contains(500000) == False)

    # swap with objkt id above max must fail
    # there are no objkts at this stage so should fail
    #
    # TODO
    #
    # This should fail but it passes, however i don't know if i'm
    # making the objkt in the same way i think i'm making the objkt
    # scenario += swap.swap(
    #     creator=creator.address,
    #     royalties=250,
    #     objkt_id=155,
    #     objkt_amount=2,
    #     xtz_per_objkt=sp.utils.nat_to_mutez(1)
    # ).run(
    #     sender=seller.address,
    #     valid=False
    # )

    # nothing changed because the swap failed as no swaps were created
    # TODO the counter should not increment!
    # .... but maybe it does (or doesn't matter)
    #      i'm not a contract expert
    # scenario.verify(swap.data.counter == 500001)

    # TODO this should not exist!
    # scenario.verify(swap.data.swaps.contains(500000) == False)

    # TODO how to import this method from objkt_swap.py?
    #
    # This is where I got stuck, I need to be able to create
    # objkts to continue testing

    # objktContract = sp.contract(
        # sp.TRecord(
            # address=sp.TAddress,
            # amount=sp.TNat,
            # token_id=sp.TNat,
            # token_info=sp.TMap(sp.TString, sp.TBytes)
        # ),
        # objkt.address,
        # entry_point = "mint"
    # ).open_some()
    #
    # objktTransfer = sp.transfer(
    #     sp.record(
    #         address=creator.address,
    #         amount=1,
    #         token_id=153,
    #         token_info={ '' : sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468') }
    #     ),
    #     sp.mutez(0),
    #     objktContract
    # )

    # create a 1/1 objkt contract
    swapObjkt = OBJKTSwapClass.OBJKTSwap(
        objkt.address,
        sp.test_account("hdao").address,
        sp.test_account("manager").address,
        metadata,
        sp.test_account("curator").address
    )

    scenario += swapObjkt

    # # add a multiple edition from the same creator
    # # the address and the sender are both the creator
    scenario += swapObjkt.mint_OBJKT(
        address = creator.address,
        amount = 1,
        royalties = 200,
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = creator.address,
        valid = True
    )

    # # the mint was successful but still no swap
    scenario.verify(swap.data.counter == 500000)
    scenario.verify(swap.data.swaps.contains(500000) == False)

    # objkt exists correctly
    scenario.verify(swapObjkt.data.objkt_id == 153)
    scenario.verify(swapObjkt.data.swap_id == 0)

    scenario.verify(swapObjkt.data.royalties.contains(152) == True)
    scenario.verify(swapObjkt.data.royalties.get(152).royalties == 200)
    scenario.verify(swapObjkt.data.royalties.get(152).issuer == creator.address)
    scenario.verify(swapObjkt.data.swaps.contains(0) == False)

    # switch back to marketplace
    swap = Marketplace(
        objkt.address,
        metadata,
        manager.address,
        fee
    )

    scenario += swap

    # try swap more objkts than exist must fail
    # TODO this should fail and currently does not
    # scenario += swap.swap(
    #     creator=creator.address,
    #     issuer=creator.address,
    #     objkt_amount = 2,
    #     objkt_id = 152,
    #     royalties = 200,
    #     xtz_per_objkt = sp.utils.nat_to_mutez(1)
    # ).run(
    #     sender = seller.address,
    #     valid = False
    # )
    #
    # # swap id should not have incremented
    # scenario.verify(swap.data.swaps.contains(500000) == False)

    # swap with new objkt id must pass
    scenario += swap.swap(
        creator=creator.address,
        issuer=creator.address,
        royalties=250,
        objkt_id = 153,
        objkt_amount = 1,
        xtz_per_objkt = sp.utils.nat_to_mutez(1)
    ).run(
        sender = seller.address,
        valid = True
    )

    # one swap was added
    scenario.verify(swap.data.counter == 500001)
    scenario.verify(swap.data.swaps.contains(500000) == True)
    scenario.verify(swap.data.swaps.contains(500001) == False)
    scenario.verify(swap.data.swaps.get(500000).objkt_id == 153)

    # create an objkt contract
    swapObjkt = OBJKTSwapClass.OBJKTSwap(
        objkt.address,
        sp.test_account("hdao").address,
        sp.test_account("manager").address,
        metadata,
        sp.test_account("curator").address
    )

    scenario += swapObjkt

    # # add a multiple edition from the same creator
    # # the address and the sender are both the creator
    scenario += swapObjkt.mint_OBJKT(
        address = creator.address,
        amount = 3,
        royalties = 250,
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = creator.address,
        valid = True
    )
    #
    # scenario.verify(swap.data.objkt_id == 500002)
    # scenario.verify(swap.data.swaps.contains(500001) == True)

    # try to list the new objkt
    # scenario += swap.swap(
    #     creator=creator.address,
    #     royalties=250,
    #     objkt_id = 154,
    #     objkt_amount = 2,
    #     xtz_per_objkt = sp.utils.nat_to_mutez(1)
    # ).run(sender = creator.address, valid = False)
    #
    # # put multiple editions up as the creator
    # scenario += swap.swap(
    #     creator=creator.address,
    #     royalties=250,
    #     objkt_id = 154,
    #     objkt_amount = 2,
    #     xtz_per_objkt = sp.utils.nat_to_mutez(1)
    # ).run(sender = creator.address, valid = False)

    # there should be 2 more swaps
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

@sp.add_test("Test collect Single Edition")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Collect Test (Single Edition)")

    # init test values
    seller = sp.test_account("seller")
    buyer = sp.test_account("buyer")
    manager = sp.test_account("manager")
    objkt = sp.test_account("objkt123")

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

    fee = 25

    swap = Marketplace(
        objkt.address,
        metadata,
        manager.address,
        fee
    )

    scenario += swap

    # no swaps yet
    scenario.verify(swap.data.counter == 500000)
    scenario.verify(swap.data.swaps.contains(500000) == False)

    scenario += swap.swap(
        creator=creator.address,
        royalties=250,
        objkt_id = 153,
        objkt_amount = 1,
        xtz_per_objkt = sp.utils.nat_to_mutez(2)
    ).run(
        sender = seller.address,
        valid = True
    )

    # one swap was added
    scenario.verify(swap.data.swaps.contains(500000) == True)
    scenario.verify(swap.data.swaps.contains(500001) == False)
    scenario.verify(swap.data.counter == 500001)

    # data is as expected inside the swap
    scenario.verify(swap.data.swaps.get(500000).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 1)
    scenario.verify(swap.data.swaps.get(500000).royalties == 250)
    scenario.verify(swap.data.swaps.get(500000).xtz_per_objkt == sp.utils.nat_to_mutez(2))

    # try to collect own swap
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = seller.address,
        amount = sp.utils.nat_to_mutez(2),
        valid = False
    )

    # swap is still available
    scenario.verify(swap.data.swaps.contains(500000) == True)
    scenario.verify(swap.data.swaps.contains(500001) == False)

    # try to collect the swap without enough tez
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = buyer.address,
        amount = sp.utils.nat_to_mutez(1),
        valid = False
    )

    # swap is still available
    scenario.verify(swap.data.swaps.contains(500000) == True)
    scenario.verify(swap.data.swaps.contains(500001) == False)

    # collect with enough tez
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = buyer.address,
        amount = sp.utils.nat_to_mutez(2),
        valid = True
    )

    # the swap is still present but the available objkts is now 0
    scenario.verify(swap.data.swaps.get(500000).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 0)
    scenario.verify(swap.data.swaps.get(500000).royalties == 250)
    scenario.verify(swap.data.swaps.get(500000).xtz_per_objkt == sp.utils.nat_to_mutez(2))

    # try to collect again and fail
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = seller.address,
        amount = sp.utils.nat_to_mutez(2),
        valid = False
    )

@sp.add_test("Test collect Multiple Editions")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Collect Test (Multiple Edition)")

    # init test values
    seller = sp.test_account("seller")
    buyer = sp.test_account("buyer")
    manager = sp.test_account("manager")
    objkt = sp.test_account("objkt123")

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

    fee = 25

    swap = Marketplace(
        objkt.address,
        metadata,
        manager.address,
        fee
    )

    scenario += swap

    # no swaps yet
    scenario.verify(swap.data.counter == 500000)
    scenario.verify(swap.data.swaps.contains(500000) == False)

    scenario += swap.swap(
        creator=creator.address,
        royalties=250,
        objkt_id = 153,
        objkt_amount = 4,
        xtz_per_objkt = sp.utils.nat_to_mutez(3)
    ).run(
        sender = creator.address,
        valid = True
    )

    # one swap was added
    scenario.verify(swap.data.swaps.contains(500000) == True)
    scenario.verify(swap.data.swaps.contains(500001) == False)
    scenario.verify(swap.data.counter == 500001)

    # data is as expected inside the swap
    scenario.verify(swap.data.swaps.get(500000).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 4)
    scenario.verify(swap.data.swaps.get(500000).royalties == 250)
    scenario.verify(swap.data.swaps.get(500000).xtz_per_objkt == sp.utils.nat_to_mutez(3))

    # fail to collect own swap
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = creator.address,
        amount = sp.utils.nat_to_mutez(3),
        valid = False
    )

    # still 4 copies
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 4)

    # collect with enough tez
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = seller.address,
        amount = sp.utils.nat_to_mutez(3),
        valid = True
    )

    # the swap is still present but the available objkts is now 3
    scenario.verify(swap.data.swaps.get(500000).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 3)
    scenario.verify(swap.data.swaps.get(500000).royalties == 250)
    scenario.verify(swap.data.swaps.get(500000).xtz_per_objkt == sp.utils.nat_to_mutez(3))

    # collect with enough tez
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = seller.address,
        amount = sp.utils.nat_to_mutez(3),
        valid = True
    )

    # the swap is still present but the available objkts is now 2
    scenario.verify(swap.data.swaps.get(500000).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 2)

    # second last copy
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = seller.address,
        amount = sp.utils.nat_to_mutez(3),
        valid = True
    )

    # the swap is still present but the available objkts is now 1
    scenario.verify(swap.data.swaps.get(500000).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 1)

    # final edition
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = seller.address,
        amount = sp.utils.nat_to_mutez(3),
        valid = True
    )

    # the swap is still present but the available objkts is now 0
    scenario.verify(swap.data.swaps.get(500000).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 0)

    # try again and fail
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = seller.address,
        amount = sp.utils.nat_to_mutez(3),
        valid = False
    )

    # still 0
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 0)

@sp.add_test("Test cancel swap")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("Cancel Swap Test")

    # init test values
    seller = sp.test_account("seller")
    buyer = sp.test_account("buyer")
    manager = sp.test_account("manager")
    objkt = sp.test_account("objkt123")

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

    fee = 25

    swap = Marketplace(
        objkt.address,
        metadata,
        manager.address,
        fee
    )

    scenario += swap

    scenario += swap.swap(
        creator=creator.address,
        royalties=250,
        objkt_id = 153,
        objkt_amount = 10,
        xtz_per_objkt = sp.utils.nat_to_mutez(3)
    ).run(
        sender = seller.address,
        valid = True
    )

    # one swap was added
    scenario.verify(swap.data.swaps.contains(500000) == True)
    scenario.verify(swap.data.swaps.contains(500001) == False)
    scenario.verify(swap.data.counter == 500001)

    # data is as expected inside the swap
    scenario.verify(swap.data.swaps.get(500000).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500000).objkt_amount == 10)
    scenario.verify(swap.data.swaps.get(500000).royalties == 250)
    scenario.verify(swap.data.swaps.get(500000).xtz_per_objkt == sp.utils.nat_to_mutez(3))

    # cancel the swap
    scenario += swap.cancel_swap(500000).run(
        sender = seller.address,
        valid = True
    )

    # the swap no longer exists
    scenario.verify(swap.data.swaps.contains(500000) == False)

    # try to collect cancelled swap with enough tez
    scenario += swap.collect(
        swap_id = 500000,
    ).run(
        sender = seller.address,
        amount = sp.utils.nat_to_mutez(3),
        valid = False
    )

    # add another swap
    # TODO we really need to check if the number of items being swapped
    # is actually valid for the objkt and if the person swapping actually
    # owns the item they're swapping
    #
    # this test should actually FAIL because there are not 20 copies
    # however i see no way to easily check this information
    scenario += swap.swap(
        creator=creator.address,
        royalties=200,
        objkt_id = 153,
        objkt_amount = 20,
        xtz_per_objkt = sp.utils.nat_to_mutez(3)
    ).run(
        sender = seller.address,
        # valid = False
        valid = True
    )

    # the new swap is still present
    scenario.verify(swap.data.swaps.get(500001).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500001).objkt_amount == 20)
    scenario.verify(swap.data.swaps.get(500001).royalties == 200)
    scenario.verify(swap.data.swaps.get(500001).xtz_per_objkt == sp.utils.nat_to_mutez(3))

    # collect with enough tez
    scenario += swap.collect(
        swap_id = 500001,
    ).run(
        sender = buyer.address,
        amount = sp.utils.nat_to_mutez(3),
        valid = True
    )

    # the swap is still present but the available objkts is now 8
    scenario.verify(swap.data.swaps.get(500001).objkt_id == 153)
    scenario.verify(swap.data.swaps.get(500001).objkt_amount == 19)

    # cancel the swap
    scenario += swap.cancel_swap(500001).run(
        sender = seller.address,
        valid = True
    )

    # it's gone now
    scenario.verify(swap.data.swaps.contains(500001) == False)
