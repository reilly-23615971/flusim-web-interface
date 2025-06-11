# Flusim Web Interface Application
# Developed by Reilly Evans
# Defines structure of model configuration guide JSON files

# Imports
from typing import Annotated, Literal
from annotated_types import Ge, Le
from pydantic import BaseModel, Field

# Type Definitions
type Age = Literal[
    'young_infant', 'infant', 'young_child', 'child', 'adolescent', 
    'young_adult', 'adult', 'older_adult', 'senior', 'older_senior'
]
type TriggerCondition = Literal[
    'none', 'timed', 'per_school_cases', 'community_cases',
    'community_rate', 'per_primary_high_school_cases'
]
type BoosterType = Literal['primary', 'booster']
type Kappa = Annotated[float, Ge(0)]
# These 3 are structurally identical, but are distinguished for readability
type Proportion = Annotated[float, Ge(0), Le(1)]
type Probability = Annotated[float, Ge(0), Le(1)]
type Efficacy = Annotated[float, Ge(0), Le(1)]


# Parameter Models

# Key-value arguments passed directly to the simulator
class commandArgument(BaseModel):
    n_runs: int = Field(
        title = 'Number of Runs', default = 24, ge = 1, description = (
            'The number of simulation runs to perform.'
        )
    )
    n_cycles: int = Field(
        title = 'Number of Cycles', default = 720, ge = 1, description = ((
            'The number of simulation cycles to '
            'run before ending the simulation.'
        ))
    )

# Probability of recovering from multiple strains at once (use in arrays)
class crossImmunity(BaseModel):
    FromStrainId: int = Field(
        title = 'Initial Strain Id', description = ((
            'The ID of the infection strain that '
            'an individual recovers from naturally.'
        ))
    )
    ToStrainId: int = Field(
        title = 'Additional Strain ID', description = ((
            'The ID of an infection strain that individuals may additionally '
            'recover from when recovering from the initial strain.'
        ))
    )
    ImmunityProportion: Proportion = Field(
        title = 'Immunity Proportion', description = ((
            'The proportion of individuals recovering from the initial strain '
            'who will also recover from the additional strain.'
        ))
    )

# Simulation parameters whose value will change at specific times (use in arrays)
class dynamicIntervention(BaseModel):
    Name: Literal[
        'work_nonattendance', 'bcc_reduction', 'school_closure', 
        'seed_rate', 'school_closure_delay' 'school_closure_duration'
    ] = Field(
        title = 'Parameter Name', description = (
            'The parameter whose value will be updated.'
        )
    )
    CycleOffset: int = Field(
        title = 'Cycle Offset', description = (
            'The simulation cycle when the parameter will be updated.'
        )
    )
    NewValue: float = Field(
        title = 'New Value', description = ('The new value of the parameter.')
    )

# Set of scenario parameters modifying the simulation
class parameters(BaseModel):
    # Seeding Parameters
    seed_rate: float = Field(
        title = 'Seeding Rate', default = 0.125, ge = 0.0, description = ((
            'The average number of infections to '
            'introduce into the simulation per cycle.'
        ))
    )
    start_day_of_week: int = Field(
        title = 'Starting Day of Week', default = 0, ge = 0, le = 6, 
        description = ((
            'The day of the week on cycle 0 of each simulation run as an '
            'integer. Zero-indexed such that Sunday is 0, Monday is 1, etc.'
        ))
    )
    seeding_duration: int = Field(
        title = 'Seeding Duration', default = 720, ge = 0, description = (
            'The number of cycles that infection seeding will occur for.'
        )
    )
    seeding_start_cycle: int = Field(
        title = 'Seeding Starting Cycle', default = 0, ge = 0, description = (
            'The first cycle in which infection seeding should occur.'
        )
    )

    # Transmission Parameters
    beta_asymptomatic: float = Field(
        title = 'Beta (Asymptomatic)', default = 0.55, ge = 0.0, 
        description = ((
            'The probability of transmission from asymptomatic '
            'individuals will be multiplied by this value.'
        ))
    )
    beta_post_symptomatic: float = Field(
        title = 'Beta (Post-Symptomatic)', default = 0.55, ge = 0.0, 
        description = ((
            'The probability of transmission from infected individuals whose '
            'symptomatic period has ended will be multiplied by this value.'
        ))
    )
    kappa_household: Kappa = Field(
        title = 'Kappa (Household)', default = 2.2, description = ((
            'The probability of transmission between two individuals located '
            'in the same household will be multiplied by this value.'
        ))
    )
    kappa_child_education: Kappa = Field(
        title = 'Kappa (Child Education)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same child education facility will be multiplied by '
            'this value.'
        ))
    )
    kappa_adult_education: Kappa = Field(
        title = 'Kappa (Adult Education)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same adult education facility will be multiplied by '
            'this value.'
        ))
    )
    kappa_workplace: Kappa = Field(
        title = 'Kappa (Workplace)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same workplace will be multiplied by this value.'
        ))
    )
    kappa_child_care: Kappa = Field(
        title = 'Kappa (Childcare)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same childcare facility will be multiplied by this value.'
        ))
    )
    kappa_hospital: Kappa = Field(
        title = 'Kappa (Hospital)', default = 1.0, description = ((
            'The probability of transmission between two individuals located '
            'in the same hospital will be multiplied by this value.'
        ))
    )
    kappa_background: Kappa = Field(
        title = 'Kappa (Background)', default = 1.0, description = ((
            'The probability of transmission between two individuals during '
            'the background phase of the simulation will be multiplied by '
            'this value.'
        ))
    )

    # Infection Parameters
    prob_asymptomatic: Probability = Field(
        title = 'Adult Asymptomatic Probability', default = 0.35, 
        description = (
            'The probability of an infected adult being asymptomatic.'
        )
    )
    prob_asymptomatic_young: Probability = Field(
        title = 'Child Asymptomatic Probability', default = 0.35, 
        description = (
            'The probability of an infected child being asymptomatic.'
        )
    )
    transmissibility_delay: int = Field(
        title = 'Transmissibility Delay', default = 10, ge = 0, 
        description = ((
            'The length of the latent period, i.e. the number of cycles '
            'before an infected individual becomes infectious themselves.'
        ))
    )
    symptom_latency: int = Field(
        title = 'Symptom Latency', default = 12, ge = 0, description = ((
            'The length of the incubation period, i.e. the number of cycles '
            'before an infected individual begins to show symptoms.'
        ))
    )
    generation_time: int = Field(
        title = 'Generation Time', default = 19, ge = 0, description = ((
            'The number of cycles before an infected individual ceases to '
            'show symptoms. Subtracting the latent period from this value '
            'provides the infectious period.'
        ))
    )
    infection_duration: int = Field(
        title = 'Infection Duration', default = 19, ge = 0, description = ((
            'The number of cycles before an infected '
            'individual is considered to have recovered.'
        ))
    )

    # Behaviour Parameters
    prob_withdrawal: Probability = Field(
        title = 'Adult Withdrawal Probability', default = 0.5, description = ((
            'The probability of an infected adult withdrawing '
            'from work after becoming symptomatic.'
        ))
    )
    prob_school_withdrawal: Probability = Field(
        title = 'Child Withdrawal Probability', default = 0.9, description = ((
            'The probability of an infected child withdrawing '
            'from school after becoming symptomatic.'
        ))
    )
    prob_hospitalisation: Probability = Field(
        title = 'Hospitalisation Probability', default = 0.0, description = ((
            'The probability of an infected individual '
            'being hospitalised if they are diagnosed.'
        ))
    )
    prob_diagnosis: Probability = Field(
        title = 'Diagnosis Probability', default = 0.5, description = ((
            'The probability of an infected individual being formally '
            'diagnosed as a case after becoming symptomatic.'
        ))
    )
    prob_child_supervision: Probability = Field(
        title = 'Child Supervision Probability', default = 1.0, description = ((
            'The probability of an adult remaining in a household (regardless '
            'of where they would otherwise go) if a child is present at said '
            'household but no other adults are present.'
        ))
    )
    withdrawal_period: int = Field(
        title = 'Adult Withdrawal Probability', default = 8, ge = 0, 
        description = ((
            'The number of cycles before an infected individual who is '
            'withdrawing from work/school will resume attending their '
            'work/school normally.'
        ))
    )

    # Health Outcome Parameters
    hospitalisation_rate: Probability = Field(
        title = 'Hospitalisation Rate', default = 0.0, description = ((
            'The probability of hospitalisation occurring if an infected '
            'individual is symptomatic. Has been tagged as needing to be '
            'checked in the base schema; use prob_hospitalisation instead.'
        ))
    )

    # Contact Parameters
    background_contact_count: float = Field(
        title = 'Background Contact Count', default = 4.0, ge = 0.0, 
        description = ((
            'The number of other individuals that are encountered by a single '
            'individual during the background phase of the simulation.'
        ))
    )
    max_class_size: int = Field(
        title = 'Maximum Class Size', default = 10, ge = 0, description = ((
            'The maximum number of individuals that can be in a '
            'single class within a child education or childcare facility.'
        ))
    )
    max_adult_class_size: int = Field(
        title = 'Maximum Adult Class Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can be '
            'in a single class within an adult education facility.'
        ))
    )
    max_workgroup_size: int = Field(
        title = 'Maximum Workgroup Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can '
            'be in a single workgroup within a workplace.'
        ))
    )
    max_neighbourgroup_size: int = Field(
        title = 'Maximum Neighbour Group Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can be '
            'in a single neighbour group within a neighbourhood.'
        ))
    )
    max_churchgroup_size: int = Field(
        title = 'Maximum Church Group Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can '
            'be in a single church group within a church.'
        ))
    )
    max_class_count: int = Field(
        title = 'Maximum Class Count', default = 1, ge = 0, description = ((
            'The maximum number of distinct classes that '
            'can exist within a single education facility.'
        ))
    )

    # Intervention Parameters
    diagnosis_delay: int = Field(
        title = 'Diagnosis Delay', default = 1, ge = 0, description = ((
            'The number of cycles before a '
            'symptomatic individual can be diagnosed.'
        ))
    )
    case_trigger_threshold: int = Field(
        title = 'Case Trigger Threshold', default = 1, ge = 0, description = ((
            'The minimum number of community cases that must be detected '
            'before an intervention with a case trigger will be triggered.'
        ))
    )
    rate_trigger_threshold: int = Field(
        title = 'Rate Trigger Threshold', default = 1, ge = 0, description = ((
            'The minimum diagnosed cases per day that must be detected '
            'before an intervention with a rate trigger will be triggered.'
        ))
    )
    rate_relaxation_threshold: int = Field(
        title = 'Rate Relaxation Threshold', default = 1, ge = 0, 
        description = ((
            'The maximum diagnosed cases per day that must be detected before '
            'an intervention with a rate relaxation trigger will be relaxed.'
        ))
    )
    maximum_trigger_count: int = Field(
        title = 'Maximum Trigger Count', default = 10, ge = 0, description = ((
            'The maximum number of times an intervention with a rate '
            'trigger threshold can be triggered in a single simulation run.'
        ))
    )
    pandemic_alert: bool = Field(
        title = 'Pandemic Alert', default = False, description = ((
            'If true, a pandemic alert will be active in the simulation, '
            'making groups social distance even if specific interventions '
            'are not active.'
        ))
    )

    # Social Distancing Parameters
    social_distance_compliance: Probability = Field(
        title = 'Social Distancing Compliance', default = 0.0, description = ((
            'The probability of an individual complying '
            'with social distancing interventions.'
        ))
    )

    # School Closure Parameters
    close_childcare: bool = Field(
        title = 'Close Childcare', default = False, description = ((
            'If true, an NPI affirming that childcare facilities '
            'should be closed will be active in the simulation.'
        ))
    )
    close_child_education: bool = Field(
        title = 'Close Child Education', default = True, description = ((
            'If true, an NPI affirming that child education facilities '
            'should be closed will be active in the simulation.'
        ))
    )
    close_adult_education: bool = Field(
        title = 'Close Adult Education', default = False, description = ((
            'If true, an NPI affirming that adult education facilities '
            'should be closed will be active in the simulation.'
        ))
    )
    school_closure_compliance: float = Field(
        title = 'School Closure Compliance', default = 0.5, ge = 0, le = 1, 
        description = ((
            'The proportion of individuals in a school '
            'who will comply with school closure NPIs.'
        ))
    )
    school_closure_trigger: TriggerCondition = Field(
        title = 'School Closure Trigger', description = ((
            'The trigger condition that will enable school '
            'closure NPIs in the simulation when fulfilled.'
        ))
    )
    school_closure_relaxation: TriggerCondition = Field(
        title = 'School Closure Relaxation Trigger', description = ((
            'The trigger condition that will disable school '
            'closure NPIs in the simulation when fulfilled.'
        ))
    )
    school_closure_duration: int = Field(
        title = 'School Closure Duration', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a school closure NPI is '
            'automatically relaxed, when school_closure_trigger '
            'is set to "timed".'
        ))
    )
    school_closure_delay: TriggerCondition = Field(
        title = 'School Closure Delay', default = 0, ge = 0, description = ((
            'The number of cycles before a school closure NPI comes '
            'into effect, when school_closure_trigger is set to "timed".'
        ))
    )

    # Withdrawal Increase Parameters
    #continue from here
    
    


# Scenario parameters with age (TODO)

# Seeded natural immunity (TODO)

# Strains (TODO)

# Vaccine coverage (TODO)

# Vaccine dose (TODO)

# Vaccine efficacy (TODO)


'''
{
  "name": "Scenario_Parameter",
  "description": "Parameters that will be populated in the Scenario_Parameter table as key/value. Search C++ code for SqliteParameterBinder for available parameters.",
  "properties": {
    "withdrawal_increase_trigger": {
        "description": "Trigger for increasing the withdrawal period",
        "$ref": "#/definitions/triggerCondition"
    },
    "withdrawal_increase_relaxation": {
        "description": "Trigger for relaxing the withdrawal period",
        "$ref": "#/definitions/triggerCondition"
    },
    "withdrawal_increase_delay": {
        "description": "The delay before the withdrawal period is increased",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "withdrawal_increase_duration": {
        "description": "The duration that the withdrawal period is increased",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "increased_withdrawal": {
        "description": "The increased withdrawal period for adults",
        "type": "number",
        "minimum": 0.0,
        "default": 0.9
    },
    "increased_withdrawal_child": {
        "description": "The increased withdrawal period for children",
        "type": "number",
        "minimum": 0.0,
        "default": 0.9
    },
    "reduced_workgroup_size": {
        "description": "Size of workgroup when workgroup_size_reduction_trigger is triggered, should be less than max_workgroup_size",
        "type": "integer",
        "minimum": 0,
        "default": 10
    },
    "reduced_workgroup_trigger": {
        "description": "Trigger for reducing the size of workgroups",
        "$ref": "#/definitions/triggerCondition"
    },
    "reduced_workgroup_relaxation": {
        "description": "Trigger for relaxing the reduced size of workgroups",
        "$ref": "#/definitions/triggerCondition"
    },
    "reduced_workgroup_delay": {
        "description": "Number of cycles before the size of workgroups is reduced",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "reduced_workgroup_duration": {
        "description": "Number of cycles that the size of workgroups is reduced",
        "type": "integer",
        "minimum": 0,
        "default": 56
    },
    "prob_work_nonattendance": {
        "description": "The probability of an individual not going to work when the work_nonattendance intervention is in effect",
        "$ref": "#/definitions/probability",
        "default": 0.5
    },
    "work_nonattendance_trigger": {
        "description": "Trigger for work nonattendance",
        "$ref": "#/definitions/triggerCondition"
    },
    "work_nonattendance_relaxation": {
        "description": "Trigger for relaxing work nonattendance",
        "$ref": "#/definitions/triggerCondition"
    },
    "work_nonattendance_delay": {
        "description": "Number of cycles after work nonattendance is triggered before it is implemented",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "work_nonattendance_duration": {
        "description": "Number of cycles that work nonattendance is in effect",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "bcc_reduction": {
        "description": "(Background Contact Count) The reduction in the number of contacts that an individual has with other individuals",
        "type": "number",
        "minimum": 0.0,
        "default": 1.0
    },
    "bcc_reduction_trigger": {
        "description": "(Background Contact Count) Trigger for reducing the number of contacts that an individual has with other individuals",
        "$ref": "#/definitions/triggerCondition"
    },
    "bcc_reduction_relaxation": {
        "description": "(Background Contact Count) Trigger for relaxing the reduction in the number of contacts that an individual has with other individuals",
        "$ref": "#/definitions/triggerCondition"
    },
    "bcc_reduction_delay": {
        "description": "(Background Contact Count) Number of cycles after bcc_reduction_trigger is triggered before the reduction in contacts is implemented",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "bcc_reduction_duration": {
        "description": "(Background Contact Count) Number of cycles that the reduction in contacts is in effect",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "diagnosed_case_isolation": {
        "description": "Boolean indicating whether diagnosed cases should be isolated",
        "type": "boolean",
        "default": false
    },
    "class_dismissal": {
        "description": "boolean indicating whether classes should be dismissed when the daily diagnosed case count exceeds the rate_trigger_threshold",
        "type": "boolean",
        "default": false
    },
    "default_hospital_size": {
        "description": "The default capacity of a hospital",
        "type": "integer",
        "minimum": 0,
        "default": 120,
        "deprecated": true
    },
    "prob_admission": {
        "description": "Probability of admission to hospital",
        "$ref": "#/definitions/probability",
        "default": 0.0,
        "deprecated": true
    },
    "prob_discharge": {
        "description": "Probability of discharge from hospital",
        "$ref": "#/definitions/probability",
        "default": 0.048304847,
        "deprecated": true
    },
    "hospital_room_size": {
        "description": "The number of beds in a hospital room",
        "type": "integer",
        "minimum": 1,
        "default": 8,
        "deprecated": true
    },
    "hospital_staff_per_room": {
        "description": "The number of staff per hospital room",
        "type": "integer",
        "minimum": 1,
        "default": 2,
        "deprecated": true
    },
    "infection_waning_cycle_delay": {
        "description": "The number of cycles after the individual has recovered from infection before immunity begins to wane",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "infection_waning_rate_per_cycle": {
        "description": "Once waning has begun, the change in the proportion of immune individuals that will become susceptible again",
        "type": "number",
        "minimum": 0.0,
        "default": 0.005
    },
    "vaccination_priority": {
        "description": "TODO: Add a description",
        "type": "array",
        "items": {
            "type": "string",
            "enum": [
                "elderly",
                "healthcare",
                "essential_workers",
                "other"
            ]
        }
    },
    "vaccine_doses": {
        "description": "The initial number of vaccine doses available",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "vaccination_first_dose_rate": {
        "description": "The daily rate at which individuals receive their first dose of the vaccine",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "vaccination_trigger": {
        "description": "Trigger type for vaccination",
        "$ref": "#/definitions/triggerCondition"
    },
    "vaccination_relaxation": {
        "description": "Trigger type for relaxing vaccination",
        "$ref": "#/definitions/triggerCondition"
    },
    "vaccination_delay": {
        "description": "Number of cycles after vaccination_trigger is triggered before vaccination is implemented",
        "type": "integer",
        "minimum": 0,
        "default": 0
    },
    "vaccination_duration": {
        "description": "Number of cycles that vaccination is in effect",
        "type": "integer",
        "minimum": 0,
        "default": 56
    }
  }
}

'''
# JSON Models
class modelGuideFile(BaseModel):
    # TODO: flesh out with more parameters; hardcode anything the user won't change
    name: str = Field(
        title = 'Name', description = (
            'The name of the simulation guide file.'
        )
    )
    description: str | None = Field(
        title = 'Description', description = (
            'A brief description of the simulations the guide file defines.'
        )
    )
    output_folder: str = Field(
        title = 'Output Folder', default = './results/', description = (
            'The folder where the scenario database files will be output.'
        )
    )
    middle_joint: str | None = Field(
        title = 'Middle Joint', default = '-interface', description = ((
            'A descriptive string that will be inserted into the names of the '
            'files generated by the simulations, between the community name '
            'and the version number.'
        ))
    )
    community_used: list[str] = Field(
        title = 'Communities Used', default = ['newcastle'], description = ((
            'The communities to repeat all scenarios across, corresponding '
            'with the names of the communities configured in '
            '"toolbox_config.json".'
        ))
    )
    '''
    #shared_overrides: 
    override_templates: list[] | None = Field(
        title = 'Communities Used', default = None, description = ((
            'The communities to repeat all scenarios across, corresponding '
            'with the names of the communities configured in '
            '"toolbox_config.json".'
        ))
    )
    '''


'''
Sample Guide JSON COnfig Files



Minimal:
{
  "name": "Simple Test",
  "output_folder": "./results/",
  "middle_joint": "-coronaV",
  "community_used": [
    "newcastle"
  ],
  "community_overrides": [
    {
      "name": "newcastle",
      "parameters": {}
    }
  ],
  "shared_overrides": {
    "parameters": {
      "Command_Argument": {
        "n_runs": 24,
        "n_cycles": 720
      },
      "Scenario_Strain": [
        {
          "StrainId": 0,
          "Beta": 0.11
        }
      ]
    }
  },
  "override_templates": [
    {
      "name": "test_1",
      "parameters": {
        "Scenario_Parameter": {
          "seed_rate": 0.125,
          "school_closure_trigger": "timed",
          "school_closure_compliance": 0.5,
          "school_closure_delay": 28,
          "withdrawal_increase_trigger": "timed",
          "withdrawal_increase_delay": 28,
          "work_nonattendance_trigger": "timed",
          "prob_work_nonattendance": 0.5,
          "work_nonattendance_delay": 28
        }
      }
    }
  ],
  "simulation_sets": [
    {
      "name": "test_set_1",
      "version": 230,
      "simulations": [
        {
          "name": "test_sim_1",
          "apply_template": [
            "test_1"
          ]
        },
        {
          "name": "test_sim_2",
          "apply_template": [
            "test_1"
          ]
        }
      ]
    }
  ]
}



SSG:
{
  "name": "Sample simulation guide",
  "description": "A simple simulation guide that shows how the simulation runner works",
  "output_folder": "./results/",
  "middle_joint": "-coronaV",
  "community_used": [
    "newcastle"
  ],
  "override_templates": [
    {
      "name": "Perth interventions",
      "description": "SC50+ICI+WN50+CCR80 delays 2 weeks, then have multi-phase school closure setting.",
      "notes": "When use intervention manipulation, remember to change numbers to 3 and onwards",
      "parameters": {
        "Scenario_Parameter": {
          "seed_rate": 0.125,
          "school_closure_trigger": "timed",
          "school_closure_compliance": 0.5,
          "school_closure_delay": 28,
          "withdrawal_increase_trigger": "timed",
          "withdrawal_increase_delay": 28,
          "work_nonattendance_trigger": "timed",
          "prob_work_nonattendance": 0.5,
          "work_nonattendance_delay": 28,
          "bcc_reduction_trigger": "timed",
          "bcc_reduction": 0.2,
          "bcc_reduction_delay": 28
        },
        "Scenario_DynamicIntervention": [
          {
            "Name": "school_closure",
            "CycleOffset": 78,
            "NewValue": 1
          },
          {
            "Name": "school_closure",
            "CycleOffset": 116,
            "NewValue": 0.75
          },
          {
            "Name": "school_closure",
            "CycleOffset": 144,
            "NewValue": 0.55
          }
        ]
      }
    }
  ],
  "community_overrides": [
    {
      "name": "newcastle",
      "parameters": {
        "Scenario_ParameterWithAgePrefix": {
          "strain_0_initial_natural_immunity": 0
        }
      }
    }
  ],
  "shared_overrides": {
    "parameters": {
      "Command_Argument": {
        "n_runs": 24,
        "n_cycles": 720
      },
      "Scenario_Strain": [
        {
          "StrainId": 0,
          "Beta": 0.11
        }
      ],
      "Scenario_Parameter": {
        "vaccination_trigger": "timed"
      }
    }
  },
  "simulation_sets": [
    {
      "name": "Surge test on SC50+WN50+CCR80 2 weeks delay",
      "version": 96,
      "simulations": [
        {
          "name": "no surge",
          "apply_template": [
            "Perth interventions"
          ]
        },
        {
          "name": "surged",
          "apply_template": [
            "Perth interventions"
          ],
          "override_setting": {
            "parameters": {
              "Scenario_DynamicIntervention": [
                {
                  "Name": "seed_rate",
                  "CycleOffset": 184,
                  "NewValue": 2.5
                },
                {
                  "Name": "seed_rate",
                  "CycleOffset": 186,
                  "NewValue": 0.125
                }
              ]
            }
          }
        }
      ]
    }
  ]
}



Beta Increase:
{
    "name": "Sample simulation guide",
    "description": "A simple simulation guide that shows how the simulation runner works",
    "output_folder": "./results/",
    "middle_joint": "-coronaV",
    "community_used": ["newcastle"],
    "override_templates": [
        {
            "name": "Perth interventions",
            "description": "SC50+ICI+WN50+CCR80 delays 2 weeks, then have multi-phase school closure setting.",
            "notes": "When use intervention manipulation, remember to change numbers to 3 and onwards",
            "Scenario_Parameter": {
                "seed_rate": 0.125,
                "school_closure_trigger": "timed",
                "school_closure_compliance": 0.5,
                "school_closure_delay": 28,
                "withdrawal_increase_trigger": "timed",
                "withdrawal_increase_delay": 28,
                "work_nonattendance_trigger": "timed",
                "prob_work_nonattendance": 0.5,
                "work_nonattendance_delay": 28,
                "bcc_reduction_trigger": "timed",
                "bcc_reduction": 0.2,
                "bcc_reduction_delay": 28
            },
            "Scenario_DynamicIntervention": [
                {
                    "Name": "school_closure",
                    "CycleOffset": 78,
                    "NewValue": 1.0
                },
                {
                    "Name": "school_closure",
                    "CycleOffset": 116,
                    "NewValue": 0.75
                },
                {
                    "Name": "school_closure",
                    "CycleOffset": 144,
                    "NewValue": 0.55
                }
            ]
        }
    ],
    "community_overrides": [
        {
            "name": "newcastle",
            "Scenario_ParameterWithAgePrefix": {
                "strain_0_initial_natural_immunity": 0.0
            }
        }
    ],
    "shared_overrides": {
        "Command_Argument": {
            "n_runs": 24,
            "n_cycles": 720
        },
        "Scenario_Parameter": {
            "vaccination_trigger": "timed"
        }
    },
    "simulation_sets": [
        {
            "name": "Surge test on SC50+WN50+CCR80 2 weeks delay",
            "version": 231,
            "simulations": [
                {
                    "name": "beta normal",
                    "apply_template": ["Perth interventions"],
                    "override_setting": {
                        "Scenario_Strain": [
                            {
                                "StrainId": 0,
                                "Beta": 0.11
                            }
                        ]
                    }
                },
                {
                    "name": "beta increase 1",
                    "apply_template": ["Perth interventions"],
                    "override_setting": {
                        "Scenario_Strain": [
                            {
                                "StrainId": 0,
                                "Beta": 0.12
                            }
                        ]
                    }
                },
                {
                    "name": "beta increase 2",
                    "apply_template": ["Perth interventions"],
                    "override_setting": {
                        "Scenario_Strain": [
                            {
                                "StrainId": 0,
                                "Beta": 0.13
                            }
                        ]
                    }
                },
                {
                    "name": "beta increase 3",
                    "apply_template": ["Perth interventions"],
                    "override_setting": {
                        "Scenario_Strain": [
                            {
                                "StrainId": 0,
                                "Beta": 0.14
                            }
                        ]
                    }
                },
                {
                    "name": "beta increase 4",
                    "apply_template": ["Perth interventions"],
                    "override_setting": {
                        "Scenario_Strain": [
                            {
                                "StrainId": 0,
                                "Beta": 0.15
                            }
                        ]
                    }
                },
                {
                    "name": "beta increase 5",
                    "apply_template": ["Perth interventions"],
                    "override_setting": {
                        "Scenario_Strain": [
                            {
                                "StrainId": 0,
                                "Beta": 0.16
                            }
                        ]
                    }
                }
            ]
        }
    ]
}
'''