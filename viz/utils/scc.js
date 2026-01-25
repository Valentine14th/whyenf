4
// scc.js

const GraphSCC = (function() {
    'use strict';

    let isSccCollapsed = false;
    let sccClusters = {};

    function toggleSccs(network, sccs, sccToggle) {
        isSccCollapsed = sccToggle.checked;

        if (isSccCollapsed) {
            clusterSccs(network, sccs);
        } else {
            openAllClusters(network);
        }
    }

    function clusterSccs(network, sccs) {
        sccClusters = {};
        sccs.forEach((scc, i) => {
            // Check if any nodes in the SCC are visible
            const allNodes = network.body.data.nodes.get();
            const visibleNodesInScc = scc.filter(nodeId => {
                const node = allNodes.find(n => n.id === nodeId);
                return node && !node.hidden;
            });

            // Only cluster if at least one node in the SCC is visible
            if (visibleNodesInScc.length === 0) {
                return;
            }

            const clusterId = `scc-${i}`;
            sccClusters[i] = clusterId;
            
            const clusterOptions = {
                joinCondition: (nodeOptions) => scc.includes(nodeOptions.id) && !nodeOptions.hidden,
                clusterNodeProperties: {
                    id: clusterId,
                    label: `SCC ${i + 1} (${visibleNodesInScc.length} nodes)`,
                    title: `SCC ${i + 1}\nNodes\n: ${visibleNodesInScc.join(',\n')}`,
                    shape: 'box',
                    color: '#f0ad4e',
                    borderWidth: 2,
                    hidden: false,  // Ensure cluster node is visible when created
                },
            };
            network.cluster(clusterOptions);
        });
    }

    function openAllClusters(network) {
        Object.values(sccClusters).forEach(clusterId => {
            if (network.isCluster(clusterId)) {
                network.openCluster(clusterId);
            }
        });
        sccClusters = {};
    }

    function refreshSccs(network, sccs) {
        // Check if SCCs exist, are defined, and are currently collapsed
        if (typeof sccs === 'undefined' || !sccs || sccs.length === 0 || !isSccCollapsed) {
            return;
        }
        // Re-cluster SCCs with updated visibility
        openAllClusters(network);
        clusterSccs(network, sccs);
    }

    function getCollapsedState() {
        return isSccCollapsed;
    }

    function setupSCCHandler(sccToggle, sccs, network) {
        if (sccToggle && typeof sccs !== 'undefined' && sccs.length > 0) {
            sccToggle.addEventListener('change', function() {
                toggleSccs(network, sccs, sccToggle);
            });
        }
    }

    return {
        toggleSccs,
        refreshSccs,
        getCollapsedState,
        setupSCCHandler
    };

})();
