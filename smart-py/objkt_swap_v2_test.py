"""Unit tests for the Marketplace class.

"""

import smartpy as sp

# Import the OBJKT and marketplace modules
objktContract = sp.io.import_script_from_url("file:smart-py/fa2.py")
marketplaceContractV1 = sp.io.import_script_from_url("file:smart-py/objkt_swap_v1.py")
marketplaceContractV2 = sp.io.import_script_from_url("file:smart-py/objkt_swap_v2.py")

def get_test_environment():
    # Create the test user accounts
    admin = sp.test_account("admin")
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")

    # Initialize the OBJKT contract
    objkt = objktContract.FA2(
        objktContract.FA2_config(),
        admin.address,
        sp.utils.metadata_of_url("ipfs://QmPCwYKmEWLCHrnT6KcHREozuDqeizioHeAWGvnaaBdCoe"))

    # Initialize the hDAO contract
    hdao = objktContract.FA2(
        objktContract.FA2_config(),
        admin.address,
        sp.utils.metadata_of_url("ipfs://QmPCwYKmEWLCHrnT6KcHREozuDqeizioHeAWGvnaaBdCoe"))

    # Initialize a dummy curate contract
    curate = sp.Contract()

    # Initialize the marketplace v1 contract
    marketplaceV1 = marketplaceContractV1.OBJKTSwap(
        objkt.address,
        hdao.address,
        admin.address,
        sp.utils.metadata_of_url("ipfs://QmWQNA1A8cKZPoaaZMuqSuLud7GQTSxbbwCXhZ76DgEqHM"),
        curate.address)

    # Initialize the marketplace v2 contract
    marketplaceV2 = marketplaceContractV2.Marketplace(
        objkt.address,
        sp.utils.metadata_of_url("ipfs://QmWQNA1A8cKZPoaaZMuqSuLud7GQTSxbbwCXhZ76DgEqHM"),
        admin.address,
        25)

    # Add all the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += objkt
    scenario += hdao
    scenario += curate
    scenario += marketplaceV1
    scenario += marketplaceV2

    # Change the OBJKT token administrator to the marketplace v1 contract
    scenario += objkt.set_administrator(marketplaceV1.address).run(sender=admin)

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario" : scenario,
        "admin" : admin,
        "user1" : user1,
        "user2" : user2,
        "objkt" : objkt,
        "hdao" : hdao,
        "curate" : curate,
        "marketplaceV1" : marketplaceV1,
        "marketplaceV2" : marketplaceV2
        }

    return testEnvironment

@sp.add_test(name="Test swap and collect")
def test_swap_and_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    user1 = testEnvironment["user1"]
    user2 = testEnvironment["user2"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV2 = testEnvironment["marketplaceV2"]
    scenario = testEnvironment["scenario"]

    # Mint an OBJKT
    scenario += marketplaceV1.mint_OBJKT(
        address=user1.address,
        amount=100,
        metadata=sp.pack("ipfs://QmYVK9epp77qmv5itE83XG1uVS6tyox7ePhxXsx6LKqysN"),
        royalties=110).run(sender=user1)

    # Swap the OBJKT in the marketplace v2 contract
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner = user1.address,
            operator=marketplaceV2.address,
            token_id=152))]).run(sender=user1)
    scenario += marketplaceV2.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=50,
        xtz_per_objkt=sp.mutez(100000),
        royalties=100,
        creator=user1.address).run(sender=user1)

    # Collect the OBJKT
    scenario += marketplaceV2.collect(
        swap_id=500000).run(sender=user2, amount=sp.mutez(100000))

    # Check that all the tez have been sent
    scenario.verify(marketplaceV2.balance == sp.mutez(0))
