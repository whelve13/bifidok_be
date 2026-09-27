import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { NavTab, Sidebar } from './components/Sidebar';
import { UniverseView } from './components/UniverseView';
import { OfferConfigurator } from './components/OfferConfigurator';
import { BusinessMatcher } from './components/BusinessMatcher';
import { DossierDrawer } from './components/DossierDrawer';
import { ConnectorHub } from './components/ConnectorHub';
import { OutreachQueue } from './components/OutreachQueue';
import { MLEngineHub } from './components/MLEngineHub';
import { DoctorModal } from './components/DoctorModal';
import { CommercialOffering, PerfectCustomerDossier } from './types';
import { getOfferingsCatalog, getOutreachQueue, prospectUniverse, stageOutreach } from './services/api';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('universe');
  const [offerings, setOfferings] = useState<CommercialOffering[]>([]);
  const [selectedOfferingKey, setSelectedOfferingKey] = useState<string>('agentic_automation');
  const [rankedCustomers, setRankedCustomers] = useState<PerfectCustomerDossier[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedDossier, setSelectedDossier] = useState<PerfectCustomerDossier | null>(null);
  const [queueCount, setQueueCount] = useState<number>(2);
  const [connectorTarget, setConnectorTarget] = useState<{ name: string; domain?: string }>({
    name: 'DHL Group',
    domain: 'dhl.com',
  });
  const [isDoctorOpen, setIsDoctorOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Initial catalog load
  useEffect(() => {
    getOfferingsCatalog()
      .then((catalog) => {
        setOfferings(catalog);
        if (catalog.length > 0) {
          setSelectedOfferingKey(catalog[0].key);
        }
      })
      .catch((err) => console.error('Failed to load offerings catalog:', err));

    getOutreachQueue()
      .then((q) => setQueueCount(q.filter((d) => d.status === 'AWAITING_HUMAN_APPROVAL').length))
      .catch(() => null);
  }, []);

  // Fetch universe whenever selected offering changes
  useEffect(() => {
    if (!selectedOfferingKey) return;
    setIsLoading(true);
    prospectUniverse(selectedOfferingKey, 16)
      .then((res) => {
        setRankedCustomers(res.ranked_customers || []);
      })
      .catch((err) => console.error('Error fetching universe:', err))
      .finally(() => setIsLoading(false));
  }, [selectedOfferingKey]);

  const handleRefreshUniverse = () => {
    if (!selectedOfferingKey) return;
    setIsLoading(true);
    prospectUniverse(selectedOfferingKey, 16)
      .then((res) => {
        setRankedCustomers(res.ranked_customers || []);
        showToast('Universe rescan complete. Propensity scores refreshed.');
      })
      .catch((err) => console.error('Error refreshing universe:', err))
      .finally(() => setIsLoading(false));
  };

  const handleOfferingCreated = (newOffering: CommercialOffering) => {
    setOfferings((prev) => [newOffering, ...prev]);
    setSelectedOfferingKey(newOffering.key);
    setCurrentTab('universe');
    showToast(`Commercial offering "${newOffering.title}" activated.`);
  };

  const handleInspectConnectors = (companyName: string, domain?: string) => {
    setConnectorTarget({ name: companyName, domain });
    setCurrentTab('connectors');
  };

  const handleStageOutreach = async (dossier: PerfectCustomerDossier) => {
    try {
      const recipient = `contact@${dossier.company.domain}`;
      const subject = `Supporting ${dossier.company.name} operational initiatives`;
      await stageOutreach({
        recipient_email: recipient,
        subject: subject,
        email_body: dossier.strategic_pitch_narrative,
        dry_run: true,
      });
      setQueueCount((prev) => prev + 1);
      showToast(`Outreach draft for ${dossier.company.name} staged in review queue.`);
    } catch (err) {
      showToast(`Failed staging outreach: ${(err as Error).message}`);
    }
  };

  const activeOffering = offerings.find(
    (o) => o.key === selectedOfferingKey || o.id === selectedOfferingKey
  );

  const customOffersCount = offerings.filter((o) => o.is_custom).length;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col antialiased text-slate-900">
      {/* Top Header */}
      <Header
        onOpenNewOffer={() => setCurrentTab('configurator')}
        onOpenDoctor={() => setIsDoctorOpen(true)}
        activeOfferingTitle={activeOffering?.title}
      />

      {/* Main Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar */}
        <Sidebar
          currentTab={currentTab}
          onSelectTab={setCurrentTab}
          queueCount={queueCount}
          customOfferCount={customOffersCount}
        />

        {/* Content View Area */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          {toastMessage && (
            <div className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-lg border border-slate-700 animate-in fade-in slide-in-from-bottom-2 duration-150">
              {toastMessage}
            </div>
          )}

          {currentTab === 'universe' && (
            <UniverseView
              offerings={offerings}
              selectedOfferingKey={selectedOfferingKey}
              onSelectOfferingKey={setSelectedOfferingKey}
              rankedCustomers={rankedCustomers}
              isLoading={isLoading}
              onRefreshUniverse={handleRefreshUniverse}
              onSelectDossier={setSelectedDossier}
              onInspectConnectors={handleInspectConnectors}
              onStageOutreach={handleStageOutreach}
              onCreateNewOffer={() => setCurrentTab('configurator')}
            />
          )}

          {currentTab === 'matcher' && (
            <BusinessMatcher
              onSelectDossier={setSelectedDossier}
              onInspectConnectors={handleInspectConnectors}
            />
          )}

          {currentTab === 'configurator' && (
            <OfferConfigurator
              onOfferingCreated={handleOfferingCreated}
              onCancel={() => setCurrentTab('universe')}
            />
          )}

          {currentTab === 'connectors' && (
            <ConnectorHub
              initialCompanyName={connectorTarget.name}
              initialDomain={connectorTarget.domain}
            />
          )}

          {currentTab === 'outreach' && <OutreachQueue />}

          {currentTab === 'ml_engine' && <MLEngineHub />}
        </main>
      </div>

      {/* Slide-over Deep Dive Account Dossier Drawer */}
      <DossierDrawer
        dossier={selectedDossier}
        onClose={() => setSelectedDossier(null)}
        onStageOutreach={handleStageOutreach}
        onInspectConnectors={handleInspectConnectors}
      />

      {/* System Preflight Health Diagnostics Modal */}
      <DoctorModal
        isOpen={isDoctorOpen}
        onClose={() => setIsDoctorOpen(false)}
      />
    </div>
  );
};

export default App;
