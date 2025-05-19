import React from 'react';
import QueryResultTable from './QueryResultTable';

const EmployeeData: React.FC = () => {
  // Sample employee data
  const employeeData = [
    { employee_identifier: 1, department_identifier: 1, employee_salary: '35000.00', employee_hire_date: '2023-03-15', employee_first_name: 'Karthikeyan', employee_last_name: 'Sundaram' },
    { employee_identifier: 2, department_identifier: 1, employee_salary: '37000.00', employee_hire_date: '2022-11-12', employee_first_name: 'Sundar', employee_last_name: 'Velmurugan' },
    { employee_identifier: 3, department_identifier: 1, employee_salary: '36000.00', employee_hire_date: '2023-01-10', employee_first_name: 'Thangavel', employee_last_name: 'Rajendran' },
    { employee_identifier: 4, department_identifier: 1, employee_salary: '34000.00', employee_hire_date: '2023-06-01', employee_first_name: 'Murugan', employee_last_name: 'Elumalai' },
    { employee_identifier: 5, department_identifier: 1, employee_salary: '39000.00', employee_hire_date: '2023-05-05', employee_first_name: 'Elango', employee_last_name: 'Natarajan' },
    { employee_identifier: 6, department_identifier: 2, employee_salary: '50000.00', employee_hire_date: '2022-11-11', employee_first_name: 'Vignesh', employee_last_name: 'Ramasamy' },
    { employee_identifier: 7, department_identifier: 2, employee_salary: '52000.00', employee_hire_date: '2023-02-20', employee_first_name: 'Sathish', employee_last_name: 'Kumaravel' },
    { employee_identifier: 8, department_identifier: 2, employee_salary: '49000.00', employee_hire_date: '2021-07-14', employee_first_name: 'Balaji', employee_last_name: 'Ganesan' },
    { employee_identifier: 9, department_identifier: 2, employee_salary: '53000.00', employee_hire_date: '2022-03-08', employee_first_name: 'Dinesh', employee_last_name: 'Muthukumaran' },
    { employee_identifier: 10, department_identifier: 2, employee_salary: '51000.00', employee_hire_date: '2023-06-12', employee_first_name: 'Praveen', employee_last_name: 'Sekar' },
    { employee_identifier: 11, department_identifier: 3, employee_salary: '30000.00', employee_hire_date: '2021-05-17', employee_first_name: 'Divya', employee_last_name: 'Sivakumar' },
    { employee_identifier: 12, department_identifier: 3, employee_salary: '32000.00', employee_hire_date: '2022-04-30', employee_first_name: 'Lakshmi', employee_last_name: 'Thirumalai' },
    { employee_identifier: 13, department_identifier: 3, employee_salary: '31000.00', employee_hire_date: '2023-08-01', employee_first_name: 'Revathi', employee_last_name: 'Chandran' },
    { employee_identifier: 14, department_identifier: 3, employee_salary: '33000.00', employee_hire_date: '2022-10-19', employee_first_name: 'Sangeetha', employee_last_name: 'Ponnusamy' },
    { employee_identifier: 15, department_identifier: 3, employee_salary: '29000.00', employee_hire_date: '2023-07-07', employee_first_name: 'Uma', employee_last_name: 'Kalyani' },
    { employee_identifier: 16, department_identifier: 4, employee_salary: '45000.00', employee_hire_date: '2023-01-01', employee_first_name: 'Saravanan', employee_last_name: 'Balasubramanian' },
    { employee_identifier: 17, department_identifier: 4, employee_salary: '47000.00', employee_hire_date: '2022-09-27', employee_first_name: 'Kannan', employee_last_name: 'Rajagopal' },
    { employee_identifier: 18, department_identifier: 4, employee_salary: '46000.00', employee_hire_date: '2021-11-20', employee_first_name: 'Manikandan', employee_last_name: 'Sankar' },
    { employee_identifier: 19, department_identifier: 4, employee_salary: '44000.00', employee_hire_date: '2023-03-22', employee_first_name: 'Ramesh', employee_last_name: 'Duraisamy' },
    { employee_identifier: 20, department_identifier: 3, employee_salary: '48000.00', employee_hire_date: '2022-06-13', employee_first_name: 'Karthik', employee_last_name: 'Selvam' }
  ];

  // Define headers
  const headers = [
    'ID', 
    'Department ID', 
    'First Name', 
    'Last Name', 
    'Salary', 
    'Hire Date'
  ];

  // Format data for the table
  const data = employeeData.map(emp => [
    emp.employee_identifier,
    emp.department_identifier,
    emp.employee_first_name,
    emp.employee_last_name,
    `$${emp.employee_salary}`,
    new Date(emp.employee_hire_date).toLocaleDateString()
  ]);

  return (
    <div className="card" style={{ 
      maxWidth: '1200px', 
      margin: '0 auto', 
      padding: '1.5rem',
      backgroundColor: 'white'
    }}>
      <h2 style={{ marginBottom: '1rem' }}>Employee Directory</h2>
      <QueryResultTable 
        headers={headers}
        data={data}
      />
    </div>
  );
};

export default EmployeeData;
