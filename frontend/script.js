// Fetch data for the tabs
const fetchData = async (url) => {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Fetch error: ', error);
    return null;
  }
};

// Render the data to the given tab
const renderData = (tabId, data) => {
  const tabDataDiv = document.getElementById(`${tabId}-data`);
  tabDataDiv.innerHTML = ''; // Clear previous content

  if (data && data.tiers) {
    Object.keys(data.tiers).forEach(tier => {
      const tierDiv = document.createElement('div');
      tierDiv.innerHTML = `<h3>${tier}</h3>`;
      
      data.tiers[tier].sources.forEach(source => {
        const sourceDiv = document.createElement('div');
        sourceDiv.innerHTML = `<strong>${source.name}</strong>: ${source.source_gained} points`;

        source.items.forEach(item => {
          const itemDiv = document.createElement('div');
          itemDiv.innerHTML = `${item.name} (${item.points} points) - Obtained: ${item.obtained ? 'Yes' : 'No'}`;
          sourceDiv.appendChild(itemDiv);
        });

        tierDiv.appendChild(sourceDiv);
      });

      tabDataDiv.appendChild(tierDiv);
    });
  } else {
    tabDataDiv.innerHTML = '<p>No data available.</p>';
  }
};

// Switch between tabs
const changeTab = (tabId) => {
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(tab => tab.classList.remove('active'));

  const contents = document.querySelectorAll('.tab-content');
  contents.forEach(content => content.classList.remove('active'));

  document.querySelector(`#${tabId}`).classList.add('active');
  document.querySelector(`[onclick="changeTab('${tabId}')"]`).classList.add('active');

  // Fetch data for the selected tab if not already loaded
  if (tabId === 'tab1' && !document.getElementById('tab1-data').hasChildNodes()) {
    fetchData('http://ironfoundry.cc:8000/api/data1').then(data => renderData('tab1', data));
  } else if (tabId === 'tab2' && !document.getElementById('tab2-data').hasChildNodes()) {
    fetchData('http://ironfoundry.cc:8000/api/data2').then(data => renderData('tab2', data));
  }
};

// Initialize tabs with default data
document.addEventListener('DOMContentLoaded', () => {
  fetchData('http://ironfoundry.cc:8000/api/data1').then(data => renderData('tab1', data));
  fetchData('http://ironfoundry.cc:8000/api/data2').then(data => renderData('tab2', data));
});
