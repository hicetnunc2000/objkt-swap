import smartpy as sp

class Proxy(sp.Contract):
    def __init__(self, addr, owner):
        self.init(
            contract = addr,
            owner = owner)

    # @param newAddr The address of the updated contract
    @sp.entry_point
    def setAddr(self, params):
        sp.verify(sp.sender == self.data.owner, message = "invalid permissions")
        self.data.contract = params.newAddr

@sp.add_test("hic et nunc proxy contract tests")
def test():
    # init test and create html output
    scenario = sp.test_scenario()
    scenario.h1("hic et nunc proxy contract")

    # init test values
    owner = sp.test_account("owner")
    notOwner = sp.test_account("notOwner")
    oldContract = sp.test_account("old")
    newContract = sp.test_account("new")

    # init contract
    proxy = Proxy(oldContract.address, owner.address)
    scenario += proxy
    # sanity check
    scenario.verify(proxy.data.contract == oldContract.address)

    # test entrypoints
    scenario.h2("[ENTRYPOINT] setAddr")
    scenario.h3("[SUCCESS-setAddr]")
    scenario += proxy.setAddr(newAddr = newContract.address).run(sender = owner)
    scenario.verify(proxy.data.contract == newContract.address)

    scenario.h3("[FAILED-setAddr] Invalid permissions")
    scenario += proxy.setAddr(newAddr = oldContract.address).run(
        sender = notOwner,
        valid = False)
