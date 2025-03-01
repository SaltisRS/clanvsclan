// script.js

$(document).ready(function () {
    // Tab switching logic
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
  
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        // Deactivate all tabs and content
        tabs.forEach(t => t.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
  
        // Activate the clicked tab and its content
        tab.classList.add('active');
        const target = tab.dataset.tab;
        document.getElementById(target).classList.add('active');
  
        // Load data for the selected tab
        if (target === 'tab1' && !document.getElementById('tab1').dataset.loaded) {
          loadAndPopulateData('tab1', 'backend/api/data1');
        } else if (target === 'tab2' && !document.getElementById('tab2').dataset.loaded) {
          loadAndPopulateData('tab2', 'backend/api/data2');
        }
      });
    });
  
    // Function to load data and populate the tab content
    function loadAndPopulateData(tabId, apiUrl) {
      fetch(apiUrl)
        .then(response => response.json())
        .then(data => {
          const tabContentElement = document.getElementById(tabId);
          tabContentElement.dataset.loaded = true; // Mark as loaded
  
          // Populate the tab content with tiers, sources, and items
          for (const tierName in data.tiers) {
            populateTier(tierName, data.tiers[tierName], tabContentElement);
          }
        })
        .catch(error => console.error('Error fetching data:', error));
    }
  
    function populateTier(tierName, tierData, tabContentElement) {
      // Create accordion elements
      const accordion = document.createElement('div');
      accordion.classList.add('accordion');
  
      const accordionHeader = document.createElement('div');
      accordionHeader.classList.add('accordion-header');
      accordionHeader.textContent = tierName;
      accordion.appendChild(accordionHeader);
  
      const accordionContent = document.createElement('div');
      accordionContent.classList.add('accordion-content');
      accordion.appendChild(accordionContent);
  
      // Create sources table
      const sourcesTable = document.createElement('table');
      sourcesTable.classList.add('sources-table', 'display'); // Add 'display' class for DataTables
      accordionContent.appendChild(sourcesTable);
  
      // Create table header
      const thead = document.createElement('thead');
      sourcesTable.appendChild(thead);
      const headerRow = document.createElement('tr');
      thead.appendChild(headerRow);
  
      const headers = ['Source Name', 'Source Gained', 'Multiplier Active', 'Actions'];
      headers.forEach(headerText => {
        const th = document.createElement('th');
        th.textContent = headerText;
        headerRow.appendChild(th);
      });
  
      // Create table body
      const tbody = document.createElement('tbody');
      sourcesTable.appendChild(tbody);
  
      // Populate sources table
      tierData.sources.forEach(source => {
        const sourceRow = document.createElement('tr');
        tbody.appendChild(sourceRow);
  
        const nameCell = document.createElement('td');
        nameCell.textContent = source.name;
        sourceRow.appendChild(nameCell);
  
        const gainedCell = document.createElement('td');
        gainedCell.textContent = source.source_gained;
        sourceRow.appendChild(gainedCell);
  
        // Add a "Multiplier Active" column
        const multiplierCell = document.createElement('td');
        sourceRow.appendChild(multiplierCell);
  
        // Check if there are any unlocked multipliers
        const hasUnlockedMultiplier = source.multipliers.some(
          multiplier => multiplier.unlocked === true
        );
  
        multiplierCell.textContent = hasUnlockedMultiplier ? 'Yes' : 'No'; // Display Yes/No
  
        if (hasUnlockedMultiplier) {
          multiplierCell.style.color = 'green';
        } else {
          multiplierCell.style.color = 'red';
        }
  
        const actionsCell = document.createElement('td');
        sourceRow.appendChild(actionsCell);
  
        const showItemsButton = document.createElement('button');
        showItemsButton.textContent = 'Show Items';
        actionsCell.appendChild(showItemsButton);
  
        // Items table (initially hidden)
        const itemsTable = document.createElement('table');
        itemsTable.classList.add('items-table');
        itemsTable.style.display = 'none'; // Hide initially
        accordionContent.appendChild(itemsTable);
  
        // Function to populate items table
        function populateItemsTable(items) {
          // Clear existing table data
          itemsTable.innerHTML = '';
  
          // Create table header
          const itemsThead = document.createElement('thead');
          itemsTable.appendChild(itemsThead);
          const itemsHeaderRow = document.createElement('tr');
          itemsThead.appendChild(itemsHeaderRow);
  
          const itemHeaders = ['Name', 'Points', 'Duplicate Points', 'Obtained', 'Duplicate Obtained'];
          itemHeaders.forEach(headerText => {
            const th = document.createElement('th');
            th.textContent = headerText;
            itemsHeaderRow.appendChild(th);
          });
  
          // Create table body
          const itemsTbody = document.createElement('tbody');
          itemsTable.appendChild(itemsTbody);
  
          // Populate items table
          items.forEach(item => {
            const itemRow = document.createElement('tr');
            itemsTbody.appendChild(itemRow);
  
            const itemValues = [item.name, item.points, item.duplicate_points, item.obtained, item.duplicate_obtained];
            itemValues.forEach((value, index) => {
              const td = document.createElement('td');
              td.textContent = value;
              itemRow.appendChild(td);
  
              // Apply color based on "Obtained" and "Duplicate Obtained"
              if (index === 0) { // Apply to the "Name" column
                if (!item.obtained && !item.duplicate_obtained) {
                  td.style.color = 'red';
                } else if (item.obtained && !item.duplicate_obtained) {
                  td.style.color = 'orange';
                } else if (item.obtained && item.duplicate_obtained) {
                  td.style.color = 'green';
                }
              }
            });
          });
        }
  
        // Event listener for show items button
        showItemsButton.addEventListener('click', () => {
          if (itemsTable.style.display === 'none') {
            itemsTable.style.display = 'table'; // Show the table
            showItemsButton.textContent = 'Hide Items';
  
            // Populate the items table if it's not already populated
            if (itemsTable.innerHTML === '') {
              populateItemsTable(source.items);
            }
          } else {
            itemsTable.style.display = 'none'; // Hide the table
            showItemsButton.textContent = 'Show Items';
          }
        });
      });
  
      // Initialize DataTables on the sources table
      $(sourcesTable).DataTable();
  
      // Accordion functionality
      $(accordionHeader).click(function () {
        $(this).next('.accordion-content').slideToggle();
        $(this).toggleClass('active');
      });
  
      // Append the accordion to the tab content
      tabContentElement.appendChild(accordion);
    }
  
    // Load data for the first tab on page load
    loadAndPopulateData('tab1', '/api/data1');
  });
  