/**
 * Event Handlers Setup
 * Centralizes all event handler registration
 */

var GraphEventHandlers = (function() {
    'use strict';
    
    function setupSearchHandlers(searchInput, checkboxItems, network, isEdgeHidden) {
        searchInput.addEventListener('input', function() {
            var filter = this.value.toLowerCase();
            var connectedNodes = GraphNodes.getVisibleNodesFromEdges(network, isEdgeHidden);
            
            var allNodes = network.body.data.nodes.get();
            var visibleNodeNames = new Set();
            allNodes.forEach(function(node) {
                if (connectedNodes.has(node.id)) {
                    visibleNodeNames.add(GraphNodes.getNodeName(node.id));
                }
            });
            
            checkboxItems.forEach(function(item) {
                var checkbox = item.querySelector('input[type="checkbox"]');
                var label = item.querySelector('label').textContent.toLowerCase();
                var isVisible = visibleNodeNames.has(checkbox.value);
                item.style.display = (label.includes(filter) && isVisible) ? 'flex' : 'none';
            });
        });
    }
    
    function setupPartitionSearchHandler(partitionSearchInput, partitionItems) {
        if (partitionSearchInput) {
            partitionSearchInput.addEventListener('input', function() {
                var filter = this.value.toLowerCase();
                partitionItems.forEach(function(item) {
                    var label = item.querySelector('label').textContent.toLowerCase();
                    item.style.display = label.includes(filter) ? 'flex' : 'none';
                });
            });
        }
    }
    
    function setupNodeCheckboxHandlers(checkboxes, selectedNodes, updateCallback, highlightCallback) {
        checkboxes.forEach(function(checkbox) {
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    selectedNodes.add(this.value);
                } else {
                    selectedNodes.delete(this.value);
                }
                updateCallback();
                highlightCallback();
            });
        });
    }
    
    function setupPartitionCheckboxHandlers(partitionCheckboxes, selectedPartitions, updateCallback, highlightCallback) {
        partitionCheckboxes.forEach(function(checkbox) {
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    selectedPartitions.add(this.value);
                } else {
                    selectedPartitions.delete(this.value);
                }
                updateCallback();
                highlightCallback();
            });
        });
    }
    
    function setupItemClickHandlers(checkboxItems) {
        checkboxItems.forEach(function(item) {
            item.addEventListener('click', function(e) {
                if (e.target.tagName !== 'INPUT') {
                    var checkbox = this.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
    }
    
    function setupPartitionItemClickHandlers(partitionItems) {
        partitionItems.forEach(function(item) {
            item.addEventListener('click', function(e) {
                if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'LABEL') {
                    var checkbox = this.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
    }
    
    function setupEdgeDirectionHandlers(edgeDirectionRadios, selectedNodes, highlightCallback) {
        edgeDirectionRadios.forEach(function(radio) {
            radio.addEventListener('change', function() {
                if (selectedNodes.size > 0) highlightCallback();
            });
        });
    }
    
    function setupFilterModeHandlers(filterModeRadios, selectedNodes, selectedPartitions, updateFilterModeCallback, highlightCallback) {
        filterModeRadios.forEach(function(radio) {
            radio.addEventListener('change', function() {
                updateFilterModeCallback();
                if (selectedNodes.size > 0 || selectedPartitions.size > 0) highlightCallback();
            });
        });
    }
    
    function setupClearButtonHandler(btnClear, selectedNodes, selectedPartitions, checkboxes, partitionCheckboxes, updateCallback, searchResults, searchInput, checkboxItems, handleEdgeVisibilityCallback) {
        btnClear.addEventListener('click', function() {
            selectedNodes.clear();
            selectedPartitions.clear();
            checkboxes.forEach(function(cb) { cb.checked = false; });
            partitionCheckboxes.forEach(function(cb) { cb.checked = false; });
            
            // Uncheck special selection checkboxes
            var selectLeafNodesCheckbox = document.getElementById('select-leaf-nodes');
            var selectSourceNodesCheckbox = document.getElementById('select-source-nodes');
            if (selectLeafNodesCheckbox) selectLeafNodesCheckbox.checked = false;
            if (selectSourceNodesCheckbox) selectSourceNodesCheckbox.checked = false;
            
            updateCallback();
            network.selectNodes([]);
            searchResults.textContent = '';
            searchInput.value = '';
            checkboxItems.forEach(function(item) { item.style.display = 'flex'; });
            
            handleEdgeVisibilityCallback();
        });
    }
    
    function setupToggleButtonHandler(toggleBtn, searchContent) {
        toggleBtn.addEventListener('click', function() {
            if (searchContent.classList.contains('hidden')) {
                searchContent.classList.remove('hidden');
                toggleBtn.textContent = 'Hide';
            } else {
                searchContent.classList.add('hidden');
                toggleBtn.textContent = 'Show';
            }
        });
    }
    
    function setupSCCHandler(sccToggle, sccs, network) {
        if (sccToggle && typeof sccs !== 'undefined' && sccs.length > 0) {
            sccToggle.addEventListener('change', function() {
                GraphSCC.toggleSccs(network, sccs, sccToggle);
            });
        }
    }
    
    function setupRankingsToggle(rankingsToggleBtn, rankingsContent, rankingsHeader) {
        if (rankingsToggleBtn && rankingsContent && rankingsHeader) {
            rankingsToggleBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (rankingsContent.classList.contains('collapsed')) {
                    rankingsContent.classList.remove('collapsed');
                    rankingsToggleBtn.textContent = 'Hide';
                } else {
                    rankingsContent.classList.add('collapsed');
                    rankingsToggleBtn.textContent = 'Show';
                }
            });
            
            rankingsHeader.addEventListener('click', function(e) {
                if (e.target !== rankingsToggleBtn) {
                    rankingsToggleBtn.click();
                }
            });
        }
    }
    
    function setupPartitionTypeHandler(partitionTypeRadios, sourcePartitions, sourcePartitionLabels, leafPartitions, leafPartitionLabels, selectedPartitions, updateCallback, highlightCallback) {
        // Function to update stats display
        function updateStatsDisplay(stats) {
            var statsDiv = document.getElementById('partition-stats');
            if (statsDiv && stats) {
                statsDiv.innerHTML = 
                    '<div style="margin-bottom: 2px;"><strong>Initial partitions:</strong> ' + stats.initial_count + '</div>' +
                    '<div style="margin-bottom: 2px;"><strong>After merging:</strong> ' + stats.merged_count + '</div>' +
                    '<div style="font-style: italic;">Strategy: ' + stats.strategy + '</div>';
            }
        }
        
        // Set initial stats for source partitions
        if (window.sourceStats) {
            updateStatsDisplay(window.sourceStats);
        }
        
        partitionTypeRadios.forEach(function(radio) {
            radio.addEventListener('change', function() {
                // Clear current selections
                selectedPartitions.clear();
                
                // Swap partition data
                if (this.value === 'source') {
                    window.partitions = sourcePartitions;
                    window.partitionLabels = sourcePartitionLabels;
                    updateStatsDisplay(window.sourceStats);
                } else if (this.value === 'leaf') {
                    window.partitions = leafPartitions;
                    window.partitionLabels = leafPartitionLabels;
                    updateStatsDisplay(window.leafStats);
                }
                
                // Rebuild partition list HTML
                var partitionList = document.getElementById('partition-list');
                if (partitionList && window.partitions) {
                    var html = '';
                    var partitionKeys = Object.keys(window.partitions);
                    for (var i = 0; i < partitionKeys.length; i++) {
                        var key = partitionKeys[i];
                        html += '<div class="checkbox-item">';
                        html += '<input type="checkbox" id="partition-' + key + '" class="partition-checkbox" value="' + key + '">';
                        html += '<label for="partition-' + key + '">' + window.partitionLabels[key] + '</label>';
                        html += '</div>';
                    }
                    partitionList.innerHTML = html;
                    
                    // Re-setup event handlers for new partition checkboxes
                    var newPartitionCheckboxes = partitionList.querySelectorAll('.partition-checkbox');
                    var newPartitionItems = partitionList.querySelectorAll('.checkbox-item');
                    
                    GraphEventHandlers.setupPartitionCheckboxHandlers(newPartitionCheckboxes, selectedPartitions, updateCallback, highlightCallback);
                    GraphEventHandlers.setupPartitionItemClickHandlers(newPartitionItems);
                    
                    // Clear partition search input and show all items
                    var partitionSearchInput = document.getElementById('partition-search-input');
                    if (partitionSearchInput) {
                        partitionSearchInput.value = '';
                    }
                    newPartitionItems.forEach(function(item) {
                        item.style.display = 'flex';
                    });
                }
                
                // Update display
                updateCallback();
                highlightCallback();
            });
        });
    }
    
    return {
        setupSearchHandlers: setupSearchHandlers,
        setupPartitionSearchHandler: setupPartitionSearchHandler,
        setupNodeCheckboxHandlers: setupNodeCheckboxHandlers,
        setupPartitionCheckboxHandlers: setupPartitionCheckboxHandlers,
        setupItemClickHandlers: setupItemClickHandlers,
        setupPartitionItemClickHandlers: setupPartitionItemClickHandlers,
        setupEdgeDirectionHandlers: setupEdgeDirectionHandlers,
        setupFilterModeHandlers: setupFilterModeHandlers,
        setupClearButtonHandler: setupClearButtonHandler,
        setupToggleButtonHandler: setupToggleButtonHandler,
        setupSCCHandler: setupSCCHandler,
        setupRankingsToggle: setupRankingsToggle,
        setupPartitionTypeHandler: setupPartitionTypeHandler
    };
})();
