# Flusim Web Interface Application
# Developed by Reilly Evans
# Defines structure of model configuration guide JSON files

# Imports
from typing import Annotated, Literal, Union, Optional
from annotated_types import Ge, Le
from typing_extensions import Self
from pydantic import BaseModel, Field, model_validator, ValidationError

# Type Definitions
type AgeGroup = Literal[
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
type EfficacyValue = Annotated[float, Ge(0), Le(1)]



# Parameter Models

# Set of scenario parameters modifying the simulation
class scenarioParameters(BaseModel):
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
            'The maximum number of times an intervention '
            'can be triggered in a single simulation run.'
        ))
    )
    pandemic_alert: bool = Field(
        title = 'Pandemic Alert', default = False, description = ((
            'If true, a pandemic alert will be active in the simulation, '
            'making groups social distance even if specific interventions '
            'are not active.'
        ))
    )

    # Isolation Parameters
    social_distance_compliance: Probability = Field(
        title = 'Social Distancing Compliance', default = 0.0, description = ((
            'The probability of an individual complying '
            'with social distancing procedures.'
        ))
    )
    diagnosed_case_isolation: bool = Field(
        title = 'Diagnosed Case Isolation', default = False, description = ((
            'If true, infected individuals who have been formally diagnosed '
            'as a case will be isolated at their household in the simulation.'
        ))
    )
    class_dismissal: bool = Field(
        title = 'Class Dismissal', default = False, description = ((
            'If true, classes at childcare and child education facilities '
            'will be dismissed when the daily diagnosed case rate exceeds '
            'rate_trigger_threshold.'
        ))
    )

    # Immunity Parameters
    infection_waning_cycle_delay: int = Field(
        title = 'Infection Waning Cycle Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before an individual who has recovered from '
            'an infection will begin to lose their immunity to the disease.'
        ))
    )
    infection_waning_rate_per_cycle: int = Field(
        title = 'Infection Waning Rate Per Cycle', default = 0.005, ge = 0.0, 
        description = ((
            'The proportion of immune individuals who will lose their '
            'immunity to the disease each cycle, once immunity waning '
            'has begun.'
        ))
    )

    # School Closure Parameters
    close_childcare: bool = Field(
        title = 'Close Childcare', default = False, description = ((
            'If true, childcare facilities will be included in '
            'the set of facilities affected by school closure NPIs.'
        ))
    )
    close_child_education: bool = Field(
        title = 'Close Child Education', default = True, description = ((
            'If true, child education facilities will be included in '
            'the set of facilities affected by school closure NPIs.'
        ))
    )
    close_adult_education: bool = Field(
        title = 'Close Adult Education', default = False, description = ((
            'If true, adult education facilities will be included in '
            'the set of facilities affected by school closure NPIs.'
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
    withdrawal_increase_trigger: TriggerCondition = Field(
        title = 'Withdrawal Increase Trigger', description = ((
            'The trigger condition that will enable withdrawal increase NPIs '
            'in the simulation when fulfilled.'
        ))
    )
    withdrawal_increase_relaxation: TriggerCondition = Field(
        title = 'Withdrawal Increase Relaxation Trigger', description = ((
            'The trigger condition that will disable withdrawal increase NPIs '
            'in the simulation when fulfilled.'
        ))
    )
    withdrawal_increase_delay: int = Field(
        title = 'Withdrawal Increase Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a withdrawal increase NPI comes into '
            'effect, when withdrawal_increase_trigger is set to "timed".'
        ))
    )
    withdrawal_increase_duration: int = Field(
        title = 'Withdrawal Increase Duration', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a withdrawal increase NPI is '
            'automatically relaxed, when withdrawal_increase_relaxation '
            'is set to "timed".'
        ))
    )
    increased_withdrawal: float = Field(
        title = 'Increased Adult Withdrawal Probability', default = 0.9, 
        ge = 0.0, description = ((
            'The probability of an infected adult withdrawing from '
            'work after becoming symptomatic, when a withdrawal increase '
            'NPI is in effect.'
        ))
    )
    increased_withdrawal_child: float = Field(
        title = 'Increased Child Withdrawal Probability', default = 0.9, 
        ge = 0.0, description = ((
            'The probability of an infected child withdrawing from '
            'school after becoming symptomatic, when a withdrawal increase '
            'NPI is in effect.'
        ))
    )

    # Reduced Workgroup Parameters
    reduced_workgroup_size: int = Field(
        title = 'Reduced Workgroup Size', default = 10, ge = 0, 
        description = ((
            'The maximum number of individuals that can be in a single '
            'workgroup within a workplace, when a reduced workgroup '
            'NPI is in effect.'
        ))
    )
    reduced_workgroup_trigger: TriggerCondition = Field(
        title = 'Reduced Workgroup Trigger', description = ((
            'The trigger condition that will enable reduced '
            'workgroup NPIs in the simulation when fulfilled.'
        ))
    )
    reduced_workgroup_relaxation: TriggerCondition = Field(
        title = 'Reduced Workgroup Relaxation Trigger', description = ((
            'The trigger condition that will disable reduced '
            'workgroup NPIs in the simulation when fulfilled.'
        ))
    )
    reduced_workgroup_delay: int = Field(
        title = 'Reduced Workgroup Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a reduced workgroup NPI comes '
            'into effect, when reduced_workgroup_trigger is set to "timed".'
        ))
    )
    reduced_workgroup_duration: int = Field(
        title = 'Reduced Workgroup Duration', default = 56, ge = 0, 
        description = ((
            'The number of cycles before a reduced workgroup NPI is '
            'automatically relaxed, when reduced_workgroup_relaxation '
            'is set to "timed".'
        ))
    )

    # Work Nonattendance Parameters
    prob_work_nonattendance: Probability = Field(
        title = 'Work Nonattendance Probability', default = 0.5, 
        description = ((
            'The probability of an infected individual not going '
            'to work, when a work nonattendance NPI is in effect.'
        ))
    )
    work_nonattendance_trigger: TriggerCondition = Field(
        title = 'Work Nonattendance Trigger', description = ((
            'The trigger condition that will enable work '
            'nonattendance NPIs in the simulation when fulfilled.'
        ))
    )
    work_nonattendance_relaxation: TriggerCondition = Field(
        title = 'Work Nonattendance Relaxation Trigger', description = ((
            'The trigger condition that will disable work '
            'nonattendance NPIs in the simulation when fulfilled.'
        ))
    )
    work_nonattendance_delay: int = Field(
        title = 'Work Nonattendance Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a work nonattendance NPI comes '
            'into effect, when work_nonattendance_trigger is set to "timed".'
        ))
    )
    work_nonattendance_duration: int = Field(
        title = 'Work Nonattendance Duration', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a work nonattendance NPI is '
            'automatically relaxed, when work_nonattendance_relaxation '
            'is set to "timed".'
        ))
    )

    # Background Contact Count Reduction Parameters
    bcc_reduction: float = Field(
        title = 'Background Contact Count Reduction', default = 1.0, ge = 0.0, 
        description = ((
            'The number of other individuals that are encountered by a single '
            'individual during the background phase of the simulation will '
            'be multiplied by this value when a BCC reduction NPI '
            'is in effect.'
        ))
    )
    bcc_reduction_trigger: TriggerCondition = Field(
        title = 'BCC Reduction Trigger', description = ((
            'The trigger condition that will enable BCC '
            'reduction NPIs in the simulation when fulfilled.'
        ))
    )
    bcc_reduction_relaxation: TriggerCondition = Field(
        title = 'BCC Reduction Relaxation Trigger', description = ((
            'The trigger condition that will disable BCC '
            'reduction NPIs in the simulation when fulfilled.'
        ))
    )
    bcc_reduction_delay: int = Field(
        title = 'BCC Reduction Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a BCC reduction NPI comes '
            'into effect, when bcc_reduction_trigger is set to "timed".'
        ))
    )
    bcc_reduction_duration: int = Field(
        title = 'BCC Reduction Duration', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a BCC reduction NPI is '
            'automatically relaxed, when bcc_reduction_relaxation '
            'is set to "timed".'
        ))
    )

    # Vaccination Parameters
    vaccination_priority: list[
        Literal['elderly', 'healthcare', 'essential_workers','other']
    ] = Field(
        title = 'Vaccination Priority', description = ((
            'A list of notable demographics in the population. Individuals '
            'who are part of demographics earlier on the list will receive '
            'vaccines before other individuals when there are not enough '
            'vaccines for everyone.'
        ))
    )
    vaccine_doses: int = Field(
        title = 'Initial Vaccine Doses', default = 0, ge = 0, 
        description = ((
            'The number of vaccine doses available '
            'at the beginning of the simulation.'
        ))
    )
    vaccination_first_dose_rate: int = Field(
        title = 'Vaccination First Dose Rate', default = 0, ge = 0, 
        description = ((
            'The daily rate at which individuals '
            'receive their first dose of the vaccine.'
        ))
    )
    vaccination_trigger: TriggerCondition = Field(
        title = 'Vaccination Trigger', description = ((
            'The trigger condition that will enable '
            'vaccination in the simulation when fulfilled.'
        ))
    )
    vaccination_relaxation: TriggerCondition = Field(
        title = 'Vaccination Relaxation Trigger', description = ((
            'The trigger condition that will disable '
            'vaccination in the simulation when fulfilled.'
        ))
    )
    vaccination_delay: int = Field(
        title = 'Vaccination Delay', default = 0, ge = 0, 
        description = ((
            'The number of cycles before a vaccination intervention comes '
            'into effect, when vaccination_trigger is set to "timed".'
        ))
    )
    vaccination_duration: int = Field(
        title = 'Vaccination Duration', default = 56, ge = 0, 
        description = ((
            'The number of cycles before a vaccination intervention is '
            'automatically relaxed, when vaccination_relaxation '
            'is set to "timed".'
        ))
    )

# Set of scenario parameters set individually for a specific age group
class ageScenarioParameters(BaseModel):
    trans: Probability = Field(
        title = 'Transmission', description = ((
            'The transmissibility for individuals in the '
            'specified age group, overriding other parameters.'
        ))
    )
    susc: Probability = Field(
        title = 'Susceptibility', description = ((
            'The susceptibility for individuals in the '
            'specified age group, overriding other parameters.'
        ))
    )
    social_distance: Probability = Field(
        title = 'Social Distancing Compliance', description = ((
            'The probability of complying with social distancing '
            'procedures for individuals in the specified age '
            'group, overriding other parameters.'
        ))
    )
    mort: Probability = Field(
        title = 'Transmission', description = ((
            'The mortality for individuals in the specified '
            'age group, overriding other parameters.'
        ))
    )

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

# Probability of recovering from multiple strains at once
class crossImmunity(BaseModel):
    FromStrainId: int = Field(
        title = 'Initial Strain ID', description = ((
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

# Simulation parameters whose value will change at specific times
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
    
# Seeding of naturally immune individuals into the population
class seededNaturalImmunity(BaseModel):
    StrainId: int = Field(
        title = 'Strain ID', description = ((
            'The ID of the infection strain that will have '
            'natural immunity seeded into the population.'
        ))
    )
    Age: Optional[AgeGroup] = Field(
        title = 'Age', description = ((
            'The age group which will have natural immunity seeded into it. '
            'If None, seeds immunity into all age groups.'
        ))
    )
    InitialProportion: Proportion = Field(
        title = 'Initial Proportion', default = 0, description = ((
            'The proportion of the population which will have natural '
            'immunity to the infection at the beginning of each '
            'simulation run (cycle 0).'
        ))
    )
    ProportionPerCycle: Proportion = Field(
        title = 'Proportion Per Cycle', default = 0, description = ((
            'The proportion of the population which will gain natural '
            'immunity to the infection at each cycle.'
        ))
    )
    TargetProportion: Proportion = Field(
        title = 'Target Proportion', default = 0, description = ((
            'When this proportion of the population is immune to the '
            'infection, the simulation will stop seeding additional natural '
            'immunity into the population.'
        ))
    )

# Parameters for different strains to simulate in the same population
class strainParameters(BaseModel):
    StrainId: int = Field(
        title = 'Strain ID', description = (
            'The integer used to refer to this infection strain.'
        )
    )
    Beta: float = Field(
        title = 'Beta', description = (
            'The transmission coefficient for this infection strain.'
        )
    )
    SeedingWeight: float = Field(
        title = 'Seeding Weight', default = 1, description = ((
            'The frequency at which this strain will be seeded into the '
            'population, proportional to other strains in the simulation'
        ))
    )

# Parameters for vaccine coverage across different age groups
class vaccineCoverage(BaseModel):
    Age: Optional[AgeGroup] = Field(
        title = 'Age', description = ((
            'The age group these parameters apply to. '
            'If None, the parameters apply to all age groups.'
        ))
    )
    Initial: Proportion = Field(
        title = 'Initial Vaccinated Proportion', description = ((
            'The proportion of the population which will be vaccinated at the '
            'beginning of each simulation run (cycle 0).'
        ))
    )
    Target: EfficacyValue = Field(
        title = 'Target Vaccinated Efficacy', description = ((
            'The proportion of the population which is being targeted for '
            'vaccination. If enough doses are available, this is the '
            'proportion of the population that will end up being vaccinated.'
        ))
    )

# Parameters for different vaccine dose types
class vaccineDose(BaseModel):
    DoseType: BoosterType = Field(
        title = 'Dose Type', description = (
            'The type of vaccine dose these parameters apply to.'
        )
    )
    Count: int = Field(
        title = 'Number of Doses', ge = 0, description = ((
            'The number of doses that will be administered to each individual '
            'for this type of vaccine dose.'
        ))
    )
    DoseSpacingCycles: int = Field(
        title = 'Dose Spacing Cycles', ge = 1, description = ((
            'The number of cycles before an individual who has '
            'received this vaccine dose can receive another one.'
        ))
    )
    WaningDelay: int = Field(
        title = 'Waning Delay', ge = 1, description = ((
            'The number of cycles before an individual who has received this '
            'vaccine dose will begin to lose their immunity to the disease.'
        ))
    )
    WaningRatePerCycle: Proportion = Field(
        title = 'Waning Rate per Cycle', description = ((
            'The proportion of vaccinated individuals who will lose their '
            'immunity to the disease each cycle, once immunity waning '
            'has begun.'
        ))
    )

# Parameters controlling efficacy of different vaccine doses
class vaccineEfficacy(BaseModel):
    DoseType: BoosterType = Field(
        title = 'Dose Type', description = (
            'The type of vaccine dose these parameters apply to.'
        )
    )
    Age: Optional[AgeGroup] = Field(
        title = 'Age', description = ((
            'The age group these parameters apply to. '
            'If None, the parameters apply to all age groups.'
        ))
    )
    Efficacy: EfficacyValue | list[EfficacyValue] = Field(
        title = 'Efficacy', description = (
            'The total population effectiveness of '
            'each primary dose / all booster doses.'
        )
    )
    WanedEfficacy: EfficacyValue = Field(
        title = 'Waned Efficacy', description = (
            'The total population effectiveness after all '
            'primary doses / each booster dose has waned.'
        )
    )

    # Efficacy should be list for primary and single value for booster
    @model_validator(mode = 'after')
    def efficacyValidation(self) -> Self:
        if self.DoseType == 'primary' and not isinstance(self.Efficacy, list):
            raise ValidationError(
                'Primary vaccines should have a list of efficacy values'
            )
        elif self.DoseType == 'booster' and not isinstance(
            self.Efficacy, EfficacyValue
        ):
            raise ValidationError(
                'Booster vaccines should have a single efficacy value'
            )
        return self

# Type union for compiling all parameter types into one object
Parameter = Union[
    scenarioParameters, ageScenarioParameters, commandArgument, 
    list[crossImmunity], list[dynamicIntervention], 
    list[seededNaturalImmunity], list[strainParameters], 
    list[vaccineCoverage], list[vaccineDose], list[vaccineEfficacy]
]



# JSON Config Models

# Model for parameters to modify in simulations on a specific community
class communityOverride(BaseModel):
    name: str = Field(
        title = 'Name', description = (
            'The name of the community these parameters apply to.'
        )
    )
    parameters: list[Parameter] = Field(
        title = 'Parameters', description = (
            'Parameters to modify for this community.'
        )
    )

# Model for templates used by simulation sets to modify parameters
class overrideTemplate(BaseModel):
    name: str = Field(
        title = 'Name', description = (
            'The name of the template.'
        )
    )
    parameters: list[Parameter] = Field(
        title = 'Parameters', description = (
            'Parameters to modify for this template.'
        )
    )

# Model for individual simulations and their parameters
class simulation(BaseModel):
    apply_template: list[str] = Field(
        title = 'Applied Templates', description = ((
            'A list of names of override templates whose '
            'parameter values will be used by this simulation.'
        ))
    )
    override_setting: Optional[list[Parameter]] = Field(
        title = 'Override Settings', description = (
            'Parameters that will be applied to this simulation alone.'
        )
    )

# Model for collections of simulations to run together
class simulationSet(BaseModel):
    name: str = Field(title = 'Name', description = ('The name of this set.'))
    version: float = Field(
        title = 'Version', description = ((
            'The set number that will be inserted into the names of the '
            'files generated by the simulations, after the version number.'
        ))
    )
    skip: bool = Field(
        title = 'Skip', description = (
            'If true, the model will not run this set of simulations.'
        )
    )
    simulations: list[simulation] = Field(
        title = 'Simulations', description = (
            'A list of scenarios to run in this set.'
        )
    )

# Model for the full configuration JSON file
class modelGuideFile(BaseModel):
    # TODO: hardcode anything the user won't change as defaults
    # TODO: validate that template/community names are correct
    name: str = Field(
        title = 'Name', description = (
            'The name of the simulation guide file.'
        )
    )
    description: Optional[str] = Field(
        title = 'Description', description = (
            'A brief description of the simulations the guide file defines.'
        )
    )
    output_folder: str = Field(
        title = 'Output Folder', default = './results/', description = (
            'The folder where the scenario database files will be output.'
        )
    )
    middle_joint: Optional[str] = Field(
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
    shared_overrides: Optional[list[Parameter]] = Field(
        title = 'Shared Overrides', description = (
            'Parameters that will be applied to all scenarios in the file.'
        )
    )
    community_overrides: Optional[list[communityOverride]] = Field(
        title = 'Community Overrides', description = ((
            'Parameters that will only be applied to '
            'simulations using specific communities'
        ))
    )
    override_templates: Optional[list[overrideTemplate]] = Field(
        title = 'Override Templates', description = ((
            'Templates containing a set of parameters that '
            'can be applied selectively to different scenarios.'
        ))
    )
    simulation_sets: list[simulationSet] = Field(
        title = 'Simulation Sets', description = (
            'A list of sets containing scenarios to run together.'
        )
    )

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