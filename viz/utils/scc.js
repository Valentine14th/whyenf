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
            const clusterId = `scc-${i}`;
            sccClusters[i] = clusterId;
            const clusterOptions = {
                joinCondition: (nodeOptions) => scc.includes(nodeOptions.id),
                clusterNodeProperties: {
                    id: clusterId,
                    label: `SCC ${i + 1} (${scc.length} nodes)`,
                    shape: 'box',
                    color: '#f0ad4e',
                    borderWidth: 2,
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

    return {
        toggleSccs
    };

})();
