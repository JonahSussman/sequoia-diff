package net.jsussman.dummyapp;

public class ExampleClass {
  public int changed;
  
  public ExampleClass() { }

  private void movedMethod() {
    System.out.println("This method was moved from the bottom of the class to the top.");
    System.out.println("It was also made private.");
    System.out.println("This line was added.");
  }
}
