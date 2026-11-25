import React, { useState } from "react";
import { Container, Spinner } from "react-bootstrap";

import { applyDisplayName } from "../bidding_round/utils/applyDisplayName.ts";
import TapirToastContainer from "../components/TapirToastContainer.tsx";
import BidEditModal from "./components/BidEditModal.tsx";
import BidsTableCard from "./components/BidsTableCard.tsx";
import ContractErrorsCard from "./components/ContractErrorsCard.tsx";
import ContractsCard, {
  CreateContractsModal,
} from "./components/ContractsCard.tsx";
import FinancingProjectionCard from "./components/FinancingProjectionCard.tsx";
import PickupFillCard from "./components/PickupFillCard.tsx";
import RollbackModal from "./components/RollbackModal.tsx";
import { useBiddingRoundResults } from "./hooks/useBiddingRoundResults.ts";
import { useRollback } from "./hooks/useRollback.ts";
import type { BiddingRoundSections } from "./types.ts";

interface BiddingRoundResultsProps {
  csrfToken: string;
}

const BiddingRoundResults: React.FC<BiddingRoundResultsProps> = ({
  csrfToken,
}) => {
  const results = useBiddingRoundResults(csrfToken);
  const rollback = useRollback({
    api: results.api,
    roundId: results.roundId,
    reload: results.reload,
    setResultMessage: results.setResultMessage,
    setToastDatas: results.setToastDatas,
  });
  const [openSections, setOpenSections] = useState<BiddingRoundSections>({
    pickupLocations: false,
    bids: false,
    contracts: false,
  });

  if (results.loading && !results.data) {
    return (
      <>
        <Container className="d-flex justify-content-center mt-5">
          <Spinner animation="border" />
        </Container>

        <TapirToastContainer
          toastDatas={results.toastDatas}
          setToastDatas={results.setToastDatas}
        />
      </>
    );
  }

  return (
    <>
      <Container fluid className="mt-4">
        <h1>
          {applyDisplayName("Beitragsrunde Auswertung", results.displayName)}
        </h1>
        {results.resultMessage && (
          <p className="text-success">{results.resultMessage}</p>
        )}
        <ContractErrorsCard errors={results.errorReport} />

        {results.data &&
          results.financingProjection &&
          results.dynamicProjection && (
            <FinancingProjectionCard
              data={results.data}
              displayName={results.displayName}
              isBidRange={results.isBidRange}
              bidLevels={results.bidLevels}
              recommendedLevel={results.recommendedLevel}
              bidRangePosition={results.bidRangePosition}
              onBidRangePositionChange={results.setBidRangePosition}
              includeAutoRenewed={results.includeAutoRenewed}
              onIncludeAutoRenewedChange={results.setIncludeAutoRenewed}
              surchargePercent={results.surchargePercent}
              onSurchargePercentChange={results.setSurchargePercent}
              surchargeOnBids={results.surchargeOnBids}
              onSurchargeOnBidsChange={results.setSurchargeOnBids}
              surchargeOnAverage={results.surchargeOnAverage}
              onSurchargeOnAverageChange={results.setSurchargeOnAverage}
              surchargeFactor={results.surchargeFactor}
              membershipIncludedInProductType={
                results.membershipIncludedInProductType
              }
              membershipFeesApply={results.membershipFeesApply}
              financingProjection={results.financingProjection}
              dynamicProjection={results.dynamicProjection}
              coverageTarget={results.coverageTarget}
              onGoToCoverageTarget={results.goToCoverageTarget}
              averageBidLocked={results.averageBidLocked}
              contractsCreatedAt={results.contractsCreatedAt}
              onLockAverageBid={results.lockAverageBid}
              onUnlockAverageBid={results.unlockAverageBid}
              twelveMonthProjection={results.twelveMonthProjection}
              showProjection={results.showProjection}
              onToggleProjection={() =>
                results.setShowProjection(!results.showProjection)
              }
              newMembersPerMonth={results.newMembersPerMonth}
              onNewMembersPerMonthChange={results.setNewMembersPerMonth}
            />
          )}

        {(results.data?.pickupLocations.length ?? 0) > 0 && (
          <PickupFillCard
            open={openSections.pickupLocations}
            onToggle={() =>
              setOpenSections((prev) => ({
                ...prev,
                pickupLocations: !prev.pickupLocations,
              }))
            }
            pickupFill={results.pickupFill}
          />
        )}

        <BidsTableCard
          open={openSections.bids}
          onToggle={() =>
            setOpenSections((prev) => ({ ...prev, bids: !prev.bids }))
          }
          roundId={results.roundId}
          members={results.members}
          autoRenewedEnabled={results.data?.autoRenewedEnabled ?? false}
          unconfirmedBidCount={results.data?.unconfirmedBidCount ?? 0}
          isBidRange={results.isBidRange}
          bidLevels={results.bidLevels}
          bidRangePosition={results.bidRangePosition}
          surchargeOnBids={results.surchargeOnBids}
          surchargePercent={results.surchargePercent}
          surchargeFactor={results.surchargeFactor}
          filter={results.filter}
          onFilterChange={results.setFilter}
          sort={results.sort}
          onSortChange={results.setSort}
          selectedBidIds={results.selectedBidIds}
          selectedAutoRenewedMemberIds={results.selectedAutoRenewedMemberIds}
          allDisplayedSelected={results.allDisplayedSelected}
          onToggleBid={results.toggleBid}
          onToggleAutoRenewedMember={results.toggleAutoRenewedMember}
          onToggleAll={results.toggleAllBids}
          onConfirmBids={results.confirmBids}
          onConfirmAllBids={results.confirmAllBids}
          averageBidLocked={results.averageBidLocked}
          hasContractSelection={results.hasContractSelection}
          canOpenContractsModal={results.canOpenContractsModal}
          onOpenContractsModal={results.openContractsModal}
          onLockAverageBid={results.lockAverageBid}
          onCreateBid={results.openCreateBidModal}
          onEditBid={results.openEditBidModal}
          onDeleteBid={results.deleteBid}
          rollbackAvailable={results.data?.rollbackAvailable ?? false}
          onRollbackAll={() => rollback.openRollbackModal(null, [])}
        />

        {results.contracts.length > 0 && (
          <ContractsCard
            open={openSections.contracts}
            onToggle={() =>
              setOpenSections((prev) => ({
                ...prev,
                contracts: !prev.contracts,
              }))
            }
            contracts={results.contracts}
            growingPeriodId={results.data?.growingPeriodId ?? null}
            rollbackUntracked={results.data?.rollbackUntracked ?? false}
            onRollback={(memberIds, memberNames) =>
              rollback.openRollbackModal(memberIds, memberNames)
            }
          />
        )}
      </Container>

      <CreateContractsModal
        show={results.showContractsModal}
        onHide={() => results.setShowContractsModal(false)}
        growingPeriodId={results.data?.growingPeriodId ?? null}
        biddableProduct={results.biddableProduct}
        biddersAveragePerMonth={
          results.dynamicProjection?.bidderAveragePerMonth ?? null
        }
        checkLoading={results.checkLoading}
        checkMessage={results.checkMessage}
        checkErrors={results.checkErrors}
        selectedBidsConfirmed={results.selectedBidsConfirmed}
        createAutoRenewed={results.createAutoRenewed}
        onCreateAutoRenewedChange={results.setCreateAutoRenewed}
        createLoading={results.createLoading}
        onRunCheck={results.runCheckContracts}
        onCreateContracts={results.createContracts}
        standardPriceSaving={results.standardPriceSaving}
        onAlignStandardPrices={results.alignStandardPrices}
      />

      <RollbackModal
        show={rollback.target !== null}
        onHide={rollback.closeRollbackModal}
        target={rollback.target}
        reason={rollback.reason}
        onReasonChange={rollback.setReason}
        force={rollback.force}
        onForceChange={rollback.setForce}
        conflicts={rollback.conflicts}
        error={rollback.error}
        loading={rollback.loading}
        onRun={rollback.runRollback}
      />

      <BidEditModal
        show={results.showBidModal}
        onHide={results.closeBidModal}
        editingBid={results.editingBid}
        member={results.bidModalMember}
        members={results.members}
        biddableProduct={results.biddableProduct}
        bidLevels={results.bidLevels}
        isBidRange={results.isBidRange}
        quantityEnabled={results.bidOptions.quantityEnabled}
        saving={results.savingBid}
        onSave={results.saveBid}
      />

      <TapirToastContainer
        toastDatas={results.toastDatas}
        setToastDatas={results.setToastDatas}
      />
    </>
  );
};

export default BiddingRoundResults;
